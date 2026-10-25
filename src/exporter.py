"""Export results as CSV and Excel files.

Cells that start with '=' or '@' are prefixed with an apostrophe so spreadsheet programs
do not run them as formulas (a known risk when opening untrusted CSV data).
"""

from io import BytesIO
from pathlib import Path

import pandas as pd

from src.config import OUTPUT_DIR, STANDARD_COLUMNS
from src.logger import get_logger

logger = get_logger()

CLEANED_COLUMN_ORDER = (
    ["source_row"] + STANDARD_COLUMNS
    + ["specialty_category", "category_source", "phone_original", "website_original",
       "phone_status", "website_status", "source_url_status",
       "is_incomplete", "needs_review", "issue_count", "quality_flags", "verification_status"]
)


def _neutralise_formulas(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in out.columns:
        out[column] = out[column].map(
            lambda v: "'" + v if isinstance(v, str) and v.startswith(("=", "@")) else v
        )
    return out


def public_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop internal columns (starting with '_')."""
    return df[[c for c in df.columns if not str(c).startswith("_")]]


def cleaned_for_export(cleaned: pd.DataFrame) -> pd.DataFrame:
    ordered = [c for c in CLEANED_COLUMN_ORDER if c in cleaned.columns]
    return _neutralise_formulas(cleaned[ordered])


def summary_table(metrics: dict, ai_summary: str = "") -> pd.DataFrame:
    labels = {
        "imported": "Records imported", "blank_rows_dropped": "Blank rows dropped",
        "duplicates_removed": "Exact duplicates removed", "cleaned": "Records after cleaning",
        "incomplete": "Incomplete records", "flagged": "Records flagged for review",
        "potential_duplicate_records": "Records in potential-duplicate pairs",
        "invalid_phone": "Invalid-looking phone numbers", "invalid_website": "Invalid-looking websites",
        "issues_total": "Total issues detected",
    }
    rows = [(labels.get(k, k), v) for k, v in metrics.items()]
    rows.append(("Note", "Automated format checks only. No record has been verified externally."))
    if ai_summary:
        rows.append(("Summary", ai_summary))
    return pd.DataFrame(rows, columns=["Measure", "Value"])


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    # utf-8-sig so Excel displays non-English characters correctly
    return _neutralise_formulas(df).to_csv(index=False).encode("utf-8-sig")


def to_excel_bytes(sheets: dict) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            _neutralise_formulas(frame).to_excel(writer, sheet_name=name[:31], index=False)
            sheet = writer.sheets[name[:31]]
            for column_cells in sheet.columns:
                longest = max((len(str(c.value)) for c in column_cells if c.value is not None), default=8)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max(longest + 2, 10), 60)
    return buffer.getvalue()


def workbook_sheets(result) -> dict:
    """Build the sheets for the Excel workbook from a PipelineResult."""
    return {
        "Summary": summary_table(result.metrics, result.ai.summary if result.ai else ""),
        "Cleaned Data": cleaned_for_export(result.cleaned),
        "Data Quality Report": result.issues,
        "Duplicates Removed": public_columns(result.removed_duplicates)[
            ["source_row", "practice_name", "city", "phone", "duplicate_of_row"]
        ] if len(result.removed_duplicates) else pd.DataFrame(
            columns=["source_row", "practice_name", "city", "phone", "duplicate_of_row"]),
        "Potential Duplicates": result.potential_pairs,
        "Change Log": result.changes,
    }


def save_outputs(result, out_dir=OUTPUT_DIR) -> dict:
    """Write cleaned CSV, quality report CSV, change log CSV and Excel workbook to disk."""
    out_dir = Path(out_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "cleaned_csv": out_dir / "cleaned_data.csv",
            "report_csv": out_dir / "data_quality_report.csv",
            "changes_csv": out_dir / "change_log.csv",
            "workbook": out_dir / "healthcare_data_results.xlsx",
        }
        paths["cleaned_csv"].write_bytes(to_csv_bytes(cleaned_for_export(result.cleaned)))
        paths["report_csv"].write_bytes(to_csv_bytes(result.issues))
        paths["changes_csv"].write_bytes(to_csv_bytes(result.changes))
        paths["workbook"].write_bytes(to_excel_bytes(workbook_sheets(result)))
    except OSError as exc:
        logger.error("Could not write output files: %s", exc)
        raise
    logger.info("Saved outputs to %s", out_dir)
    return paths
