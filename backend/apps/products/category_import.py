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
import csv
import io

from django.db import transaction

from .models import Category

MAX_FILE_BYTES = 1024 * 1024  # 1 MB is thousands of categories
NAME_MAX_LENGTH = Category._meta.get_field("name").max_length


class CategoryImportError(Exception):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def import_categories(uploaded_file):
    """Return (created_names, skipped_names). Raises CategoryImportError."""
    if uploaded_file.size > MAX_FILE_BYTES:
        raise CategoryImportError(["The file is larger than 1 MB."])
    try:
        # utf-8-sig drops the byte-order mark Excel adds when saving as CSV UTF-8
        text = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CategoryImportError(["The file isn't UTF-8 text. In Excel, save it as \"CSV UTF-8\"."])

    reader = csv.DictReader(io.StringIO(text))
    headers = {(h or "").strip().lower() for h in reader.fieldnames or []}
    if "name" not in headers:
        raise CategoryImportError(['The first row must be a header with a "name" column (and optionally "parent").'])

    errors = []
    rows = []  # (line, name, parent_name)
    seen = {}  # lowercased name -> line it first appeared on
    for row in reader:
        line = reader.line_num
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items() if k}
        name, parent = row.get("name", ""), row.get("parent", "")
        if not name and not parent:
            continue  # blank line
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

    if not rows and not errors:
        raise CategoryImportError(["The file has no categories in it."])

    existing = {c.name.lower(): c for c in Category.objects.all()}
    for line, name, parent in rows:
        if parent and parent.lower() not in existing and parent.lower() not in seen:
            errors.append(f"Line {line}: parent \"{parent}\" doesn't exist and isn't in this file.")
    if errors:
        errors.sort(key=lambda e: int(e.split(":")[0].removeprefix("Line ")))
        raise CategoryImportError(errors)

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
                raise CategoryImportError([
                    f"Line {line}: \"{name}\" and its parent \"{parent}\" are each other's parents (directly or through other rows)."
                    for line, name, parent in remaining
                ])
            pending = remaining

    return created, skipped
