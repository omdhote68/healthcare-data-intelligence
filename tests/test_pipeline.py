"""End-to-end tests using the fictional sample file."""

import pandas as pd

from src.config import SAMPLE_FILE
from src.exporter import save_outputs
from src.pipeline import run_pipeline


def test_sample_file_metrics_match_the_deliberate_errors():
    result = run_pipeline(SAMPLE_FILE)
    m = result.metrics
    assert m["imported"] == 11
    assert m["duplicates_removed"] == 1       # row 2 duplicates row 1
    assert m["cleaned"] == 10
    assert m["incomplete"] == 3               # rows 5 (phone), 6 (city), 9 (specialty)
    assert m["potential_duplicate_records"] == 2   # rows 3 and 11
    assert m["invalid_phone"] == 1            # row 7
    assert m["invalid_website"] == 2          # rows 7 and 9
    assert m["flagged"] == 6                  # rows 3, 5, 6, 7, 9, 11


def test_nothing_is_invented():
    result = run_pipeline(SAMPLE_FILE)
    row5 = result.cleaned[result.cleaned["source_row"] == 5].iloc[0]
    assert pd.isna(row5["phone"])             # missing phone stays missing
    row6 = result.cleaned[result.cleaned["source_row"] == 6].iloc[0]
    assert pd.isna(row6["city"]) and pd.isna(row6["source_url"])


def test_original_values_are_preserved_for_audit():
    result = run_pipeline(SAMPLE_FILE)
    row11 = result.cleaned[result.cleaned["source_row"] == 11].iloc[0]
    assert row11["phone_original"] == "022 5550 1234"
    assert "phone" in set(result.changes["field"])


def test_outputs_are_written_and_readable(tmp_path):
    result = run_pipeline(SAMPLE_FILE)
    paths = save_outputs(result, tmp_path)
    for path in paths.values():
        assert path.exists() and path.stat().st_size > 0
    cleaned = pd.read_csv(paths["cleaned_csv"], encoding="utf-8-sig")
    assert len(cleaned) == 10
    assert not any(c.startswith("_") for c in cleaned.columns)       # internal columns removed
    sheets = pd.ExcelFile(paths["workbook"]).sheet_names
    assert "Cleaned Data" in sheets and "Data Quality Report" in sheets


def test_messy_column_names_and_missing_columns_work(tmp_path):
    path = tmp_path / "messy.csv"
    pd.DataFrame({"CLINIC NAME": ["a clinic", "A Clinic"], "Town": ["pune", "Pune"],
                  "Tel": ["98765 55501", "98765-55501"]}).to_csv(path, index=False)
    result = run_pipeline(path)
    assert result.metrics["duplicates_removed"] == 1
    assert result.notes                                   # explains the columns not found


def test_formula_like_cells_are_neutralised_in_export(tmp_path):
    path = tmp_path / "formula.csv"
    pd.DataFrame({"Practice Name": ["=HYPERLINK(\"http://bad\")"], "City": ["Pune"]}).to_csv(path, index=False)
    paths = save_outputs(run_pipeline(path), tmp_path / "out")
    text = paths["cleaned_csv"].read_text(encoding="utf-8-sig")
    assert "'=HYPERLINK" in text
