"""Reading CSV files uploaded in Django admin, shared by the category and catalogue imports."""
import csv
import io

MAX_FILE_BYTES = 1024 * 1024  # 1 MB is thousands of rows


class CSVImportError(Exception):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def _column_key(header):
    # "Product_Name", "product name" and " PRODUCT_NAME " all mean product_name
    return "_".join((header or "").strip().lower().replace("_", " ").split())


def read_rows(uploaded_file, required_columns):
    """
    Return [(line_number, {column: value}), ...] with column names normalised
    (lowercase, underscores) and values stripped. Blank lines are dropped.
    Raises CSVImportError if the file can't be read or a column is missing.
    """
    if uploaded_file.size > MAX_FILE_BYTES:
        raise CSVImportError(["The file is larger than 1 MB."])
    try:
        # utf-8-sig drops the byte-order mark Excel adds when saving as CSV UTF-8
        text = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CSVImportError(["The file isn't UTF-8 text. In Excel, save it as \"CSV UTF-8\"."])

    reader = csv.DictReader(io.StringIO(text))
    headers = {_column_key(h) for h in reader.fieldnames or []}
    missing = [c for c in required_columns if c not in headers]
    if missing:
        raise CSVImportError([
            "The first row must be a header with these columns: " + ", ".join(required_columns)
            + ". Missing: " + ", ".join(missing) + "."
        ])

    rows = []
    for row in reader:
        values = {_column_key(k): (v or "").strip() for k, v in row.items() if k}
        if any(values.values()):
            rows.append((reader.line_num, values))
    if not rows:
        raise CSVImportError(["The file has no rows after the header."])
    return rows


def raise_if_errors(errors):
    """Raise CSVImportError with errors sorted by their "Line N:" prefix."""
    if errors:
        errors.sort(key=lambda e: int(e.split(":")[0].removeprefix("Line ")) if e.startswith("Line ") else 0)
        raise CSVImportError(errors)
