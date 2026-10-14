"""
Bulk-create categories from a CSV file uploaded in Django admin.

Format: a header row, then one category per row.

    name,parent
    Vegetables,
    Leafy Greens,Vegetables
    Fruit,
    Citrus,Fruit

`parent` is optional. It names a category that already exists or appears
anywhere in the same file. Names are matched ignoring case, so "herbs" and
"Herbs" are the same category. Categories that already exist are skipped and
left unchanged.

The file is all-or-nothing: if any row has a problem, nothing is created and
every problem is reported with its line number.
"""
from django.db import transaction

from .csv_import import CSVImportError, raise_if_errors, read_rows
from .models import Category

NAME_MAX_LENGTH = Category._meta.get_field("name").max_length


def import_categories(uploaded_file):
    """Return (created_names, skipped_names). Raises CSVImportError."""
    errors = []
    rows = []  # (line, name, parent_name)
    seen = {}  # lowercased name -> line it first appeared on
    for line, row in read_rows(uploaded_file, required_columns=["name"]):
        name, parent = row.get("name", ""), row.get("parent", "")
        if not name:
            errors.append(f"Line {line}: name is empty.")
            continue
        if len(name) > NAME_MAX_LENGTH:
            errors.append(f"Line {line}: \"{name}\" is longer than {NAME_MAX_LENGTH} characters.")
            continue
        if name.lower() in seen:
            errors.append(f"Line {line}: \"{name}\" is already on line {seen[name.lower()]}.")
            continue
        if parent.lower() == name.lower():
            errors.append(f"Line {line}: \"{name}\" can't be its own parent.")
            continue
        seen[name.lower()] = line
        rows.append((line, name, parent))

    existing = {c.name.lower(): c for c in Category.objects.all()}
    for line, name, parent in rows:
        if parent and parent.lower() not in existing and parent.lower() not in seen:
            errors.append(f"Line {line}: parent \"{parent}\" doesn't exist and isn't in this file.")
    raise_if_errors(errors)

    created, skipped = [], []
    pending = []
    for line, name, parent in rows:
        if name.lower() in existing:
            skipped.append(existing[name.lower()].name)
        else:
            pending.append((line, name, parent))

    with transaction.atomic():
        # Parents can appear after their children in the file, so create in
        # passes: each pass creates every row whose parent now exists.
        while pending:
            remaining = []
            for line, name, parent in pending:
                if parent and parent.lower() not in existing:
                    remaining.append((line, name, parent))
                    continue
                category = Category.objects.create(
                    name=name,
                    parent_category=existing[parent.lower()] if parent else None,
                )
                existing[name.lower()] = category
                created.append(name)
            if len(remaining) == len(pending):
                # Nothing could be created: the parents form a loop (A under B, B under A)
                raise CSVImportError([
                    f"Line {line}: \"{name}\" and its parent \"{parent}\" are each other's parents (directly or through other rows)."
                    for line, name, parent in remaining
                ])
            pending = remaining

    return created, skipped
