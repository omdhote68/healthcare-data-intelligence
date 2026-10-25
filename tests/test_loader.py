"""Tests for src/loader.py."""

import pandas as pd
import pytest

from src.config import DATA_DIR, STANDARD_COLUMNS
from src.loader import LoaderError, load_file, map_columns, normalise_column_name


def test_normalise_column_name_ignores_case_spaces_and_symbols():
    assert normalise_column_name("Phone Number") == "phonenumber"
    assert normalise_column_name("phone_number") == "phonenumber"
    assert normalise_column_name("PHONE-NUMBER") == "phonenumber"


def test_map_columns_recognises_aliases():
    mapping = map_columns(["Clinic Name", "Speciality", "Telephone", "Town", "URL", "Doctor"])
    assert mapping["practice_name"] == "Clinic Name"
    assert mapping["specialty"] == "Speciality"
    assert mapping["phone"] == "Telephone"
    assert mapping["city"] == "Town"
    assert mapping["website"] == "URL"
    assert mapping["doctor_name"] == "Doctor"


def test_exact_standard_name_beats_generic_alias():
    mapping = map_columns(["Name", "Practice Name"])
    assert mapping["practice_name"] == "Practice Name"


def test_load_sample_file_maps_every_column():
    result = load_file(DATA_DIR / "sample_practices.csv")
    assert len(result.data) == 11
    assert result.missing_standard_columns == []
    assert result.ignored_columns == []
    assert list(result.data.columns) == ["source_row"] + STANDARD_COLUMNS


def test_missing_columns_are_added_empty_not_invented(tmp_path):
    path = tmp_path / "small.csv"
    pd.DataFrame({"Practice Name": ["A Clinic"], "City": ["Pune"]}).to_csv(path, index=False)
    result = load_file(path)
    assert "phone" in result.missing_standard_columns
    assert result.data["phone"].isna().all()
    assert result.data["city"].iloc[0] == "Pune"


def test_extra_columns_are_reported_as_ignored(tmp_path):
    path = tmp_path / "extra.csv"
    pd.DataFrame({"Practice Name": ["A"], "Internal Notes": ["x"]}).to_csv(path, index=False)
    assert load_file(path).ignored_columns == ["Internal Notes"]


def test_blank_rows_are_dropped_and_counted(tmp_path):
    path = tmp_path / "blank.csv"
    pd.DataFrame({"Practice Name": ["A Clinic", None], "City": ["Pune", None]}).to_csv(path, index=False)
    result = load_file(path)
    assert len(result.data) == 1
    assert result.empty_rows_dropped == 1


def test_leading_zeros_in_phone_are_preserved(tmp_path):
    path = tmp_path / "zeros.csv"
    pd.DataFrame({"Practice Name": ["A"], "Phone": ["0712555042"]}).to_csv(path, index=False)
    assert load_file(path).data["phone"].iloc[0] == "0712555042"


def test_excel_file_loads(tmp_path):
    path = tmp_path / "practices.xlsx"
    pd.DataFrame({"Clinic": ["A Clinic"], "Tel": ["12345"]}).to_excel(path, index=False)
    assert load_file(path).data["practice_name"].iloc[0] == "A Clinic"


def test_missing_practice_name_column_raises_clear_error(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"City": ["Pune"], "Phone": ["123"]}).to_csv(path, index=False)
    with pytest.raises(LoaderError, match="practice name"):
        load_file(path)


def test_unsupported_extension_raises(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello")
    with pytest.raises(LoaderError, match="Unsupported"):
        load_file(path)


def test_missing_file_raises(tmp_path):
    with pytest.raises(LoaderError, match="not found"):
        load_file(tmp_path / "nope.csv")


def test_header_only_file_raises(tmp_path):
    path = tmp_path / "header_only.csv"
    path.write_text("Practice Name,City\n")
    with pytest.raises(LoaderError, match="no data rows"):
        load_file(path)
