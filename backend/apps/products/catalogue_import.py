"""
Bulk-create catalogue items (the products farmers can pick from) from a CSV
file uploaded in Django admin.

Format: a header row, then one product per row.

    Product_ID,Category,Subcategory,Product_Name,Typical_Sales_Unit
    SA0001,Vegetables,Root vegetables,Carrot,kg
    SA0109,Fruits,Citrus,Orange,kg

Subcategory is optional; without one the product goes straight into Category.
Missing categories and subcategories are created (Subcategory under Category).
Header names ignore case, spaces and underscores. Category and product names
are matched ignoring case. Products whose Product_ID already exists are skipped
and left unchanged; edit those in admin.

The file is all-or-nothing: if any row has a problem, nothing is created and
every problem is reported with its line number.
"""
from django.db import transaction

from .csv_import import raise_if_errors, read_rows
from .models import CatalogueItem, Category

COLUMNS = ["product_id", "category", "subcategory", "product_name", "typical_sales_unit"]
REQUIRED = ["product_id", "category", "product_name", "typical_sales_unit"]
MAX_LENGTHS = {
    "product_id": CatalogueItem._meta.get_field("code").max_length,
    "category": Category._meta.get_field("name").max_length,
    "subcategory": Category._meta.get_field("name").max_length,
    "product_name": CatalogueItem._meta.get_field("name").max_length,
    "typical_sales_unit": CatalogueItem._meta.get_field("default_unit").max_length,
}


def import_catalogue(uploaded_file):
    """
    Return (created_item_names, created_category_names, skipped_item_names).
    Raises CSVImportError.
    """
    errors = []
    rows = []
    codes_seen, names_seen = {}, {}
    for line, row in read_rows(uploaded_file, required_columns=REQUIRED):
        row = {c: row.get(c, "") for c in COLUMNS}
        problems = [f"{c} is empty" for c in REQUIRED if not row[c]]
        problems += [
            f"{c} is longer than {n} characters" for c, n in MAX_LENGTHS.items() if len(row[c]) > n
        ]
        if row["subcategory"] and row["subcategory"].lower() == row["category"].lower():
            problems.append("subcategory can't be the same as category")
        code, name = row["product_id"].lower(), row["product_name"].lower()
        if code and code in codes_seen:
            problems.append(f"Product_ID {row['product_id']} is already on line {codes_seen[code]}")
        if name and name in names_seen:
            problems.append(f"\"{row['product_name']}\" is already on line {names_seen[name]}")
        if problems:
            errors.append(f"Line {line}: " + "; ".join(problems) + ".")
            continue
        codes_seen[code], names_seen[name] = line, line
        rows.append((line, row))

    # Every category name must mean one place in the tree: a top-level
    # category, or a subcategory of one particular category.
    categories = {c.name.lower(): c for c in Category.objects.select_related("parent_category")}
    parent_of = {}  # lowercased name -> lowercased parent name, or None for top level
    for name, c in categories.items():
        parent_of[name] = c.parent_category.name.lower() if c.parent_category else None

    def describe(parent):
        return "a top-level category" if parent is None else f"a subcategory of \"{categories[parent].name if parent in categories else file_names.get(parent, parent)}\""

    file_names = {}  # lowercased name -> original spelling, for categories created from this file
    reported = set()  # report each misplaced category once, not on every row that uses it
    for line, row in rows:
        placements = [(row["category"], None)]
        if row["subcategory"]:
            placements.append((row["subcategory"], row["category"].lower()))
        for name, parent in placements:
            key = name.lower()
            if key in parent_of and parent_of[key] != parent:
                if (key, parent) in reported:
                    continue
                reported.add((key, parent))
                where = "already exists" if key in categories else "is earlier in this file"
                errors.append(f"Line {line}: \"{name}\" {where} as {describe(parent_of[key])}, not {describe(parent)}.")
            else:
                parent_of[key] = parent
                file_names.setdefault(key, name)

    items_by_code = {i.code.lower(): i for i in CatalogueItem.objects.all()}
    items_by_name = {i.name.lower(): i for i in items_by_code.values()}
    for line, row in rows:
        existing = items_by_name.get(row["product_name"].lower())
        if existing and existing.code.lower() != row["product_id"].lower():
            errors.append(
                f"Line {line}: \"{row['product_name']}\" already exists in the catalogue as {existing.code}."
            )
    raise_if_errors(errors)

    created_items, created_categories, skipped = [], [], []
    with transaction.atomic():
        def get_category(name, parent):
            key = name.lower()
            if key not in categories:
                categories[key] = Category.objects.create(
                    name=file_names[key],
                    parent_category=categories[parent] if parent else None,
                )
                created_categories.append(categories[key].name)
            return categories[key]

        for line, row in rows:
            if row["product_id"].lower() in items_by_code:
                skipped.append(items_by_code[row["product_id"].lower()].name)
                continue
            category = get_category(row["category"], None)
            if row["subcategory"]:
                category = get_category(row["subcategory"], row["category"].lower())
            CatalogueItem.objects.create(
                code=row["product_id"],
                name=row["product_name"],
                category=category,
                default_unit=row["typical_sales_unit"],
            )
            created_items.append(row["product_name"])

    return created_items, created_categories, skipped
