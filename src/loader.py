"""Load a CSV or Excel file and map its columns to our standard schema.

This module does NOT clean values. It only:
  1. reads the file safely (everything as text, so phone numbers keep leading zeros)
  2. figures out which file column matches which standard column
  3. reports what was missing or ignored
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.config import COLUMN_ALIASES, MAX_ROWS, STANDARD_COLUMNS
from src.logger import get_logger

logger = get_logger()

SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


class LoaderError(Exception):
    """Raised when a file cannot be loaded. The message is safe to show to users."""


@dataclass
class LoadResult:
    """Everything the loader learned about the file."""

    data: pd.DataFrame
    column_mapping: dict = field(default_factory=dict)             # standard -> original column
    missing_standard_columns: list = field(default_factory=list)   # not found in the file
    ignored_columns: list = field(default_factory=list)            # in the file, not used
    rows_in_file: int = 0
    empty_rows_dropped: int = 0


def normalise_column_name(name) -> str:
    """Lowercase and remove everything except letters and digits.

    'Phone Number', 'phone_number' and 'PHONE-NUMBER' all become 'phonenumber'.
    """
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def map_columns(columns) -> dict:
    """Match file columns to standard columns. Returns {standard: original}.

    The exact standard name is tried first, then the aliases in order,
    so a column called 'Practice Name' wins over a column called 'Name'.
    Each file column can only be used once.
    """
    normalised = {col: normalise_column_name(col) for col in columns}
    used = set()
    mapping = {}

    for standard in STANDARD_COLUMNS:
        candidates = [normalise_column_name(standard)] + COLUMN_ALIASES[standard]
        found = False
        for candidate in candidates:
            for original, norm in normalised.items():
                if original not in used and norm == candidate:
                    mapping[standard] = original
                    used.add(original)
                    found = True
                    break
            if found:
                break
    return mapping


def _file_name(source, filename) -> str:
    if filename:
        return filename
    if isinstance(source, (str, Path)):
        return str(source)
    return getattr(source, "name", "")


def _read_raw(source, filename: str) -> pd.DataFrame:
    """Read the file as text. Raises LoaderError with a friendly message on failure."""
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise LoaderError(
            f"Unsupported file type '{extension or 'unknown'}'. "
            "Please upload a .csv or .xlsx file."
        )

    try:
        if extension == ".csv":
            try:
                return pd.read_csv(source, dtype=str, encoding="utf-8-sig")
            except UnicodeDecodeError:
                if hasattr(source, "seek"):
                    source.seek(0)
                logger.warning("File is not UTF-8; retrying with latin-1 encoding.")
                return pd.read_csv(source, dtype=str, encoding="latin-1")
        return pd.read_excel(source, dtype=str, engine="openpyxl")
    except FileNotFoundError:
        raise LoaderError(f"File not found: {filename}")
    except pd.errors.EmptyDataError:
        raise LoaderError("The file is empty.")
    except pd.errors.ParserError as exc:
        raise LoaderError(f"The file could not be parsed as a table: {exc}")
    except Exception as exc:  # noqa: BLE001 - last resort, turned into a friendly message
        logger.exception("Unexpected error while reading file")
        raise LoaderError(f"Could not read the file: {exc}")


def load_file(source, filename: str = None) -> LoadResult:
    """Load a CSV/Excel file (path or uploaded file object) into the standard schema."""
    name = _file_name(source, filename)
    logger.info("Loading file: %s", name)

    raw = _read_raw(source, name)
    if raw.empty:
        raise LoaderError("The file has column headings but no data rows.")
    if len(raw) > MAX_ROWS:
        raise LoaderError(
            f"The file has {len(raw):,} rows. This demo supports up to {MAX_ROWS:,} rows."
        )

    raw.columns = [str(c).strip() for c in raw.columns]
    rows_in_file = len(raw)
    blank_rows = raw.fillna("").apply(lambda col: col.astype(str).str.strip()).eq("").all(axis=1)
    raw = raw[~blank_rows]
    empty_dropped = int(blank_rows.sum())
    if raw.empty:
        raise LoaderError("The file contains no usable rows (all rows were blank).")

    mapping = map_columns(raw.columns)
    if "practice_name" not in mapping:
        raise LoaderError(
            "Could not find a practice name column. Expected a heading such as "
            f"'Practice Name', 'Clinic Name' or 'Hospital Name'. Found: {list(raw.columns)}"
        )

    # Build the standardised table. Missing columns stay empty (we never invent data).
    standard = pd.DataFrame(index=raw.index)
    standard["source_row"] = raw.index + 1  # position among the file's data rows, for audit
    for column in STANDARD_COLUMNS:
        if column in mapping:
            standard[column] = raw[mapping[column]]
        else:
            standard[column] = pd.NA
    standard = standard.reset_index(drop=True)

    used_originals = set(mapping.values())
    result = LoadResult(
        data=standard,
        column_mapping=mapping,
        missing_standard_columns=[c for c in STANDARD_COLUMNS if c not in mapping],
        ignored_columns=[c for c in raw.columns if c not in used_originals],
        rows_in_file=rows_in_file,
        empty_rows_dropped=empty_dropped,
    )
    logger.info(
        "Loaded %d rows (%d blank dropped). Mapped: %s. Missing: %s. Ignored: %s",
        len(standard), empty_dropped, mapping,
        result.missing_standard_columns, result.ignored_columns,
    )
    return result
