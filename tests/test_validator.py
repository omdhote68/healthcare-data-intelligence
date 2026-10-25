"""Tests for src/validator.py."""

import pandas as pd

from src.cleaner import clean_dataframe
from src.config import VERIFICATION_LABEL
from src.dedupe import find_duplicates
from src.validator import add_quality_flags, validate_records


def _run(rows):
    df = pd.DataFrame(rows, columns=["practice_name", "doctor_name", "specialty", "city",
                                     "phone", "website", "source_url"])
    df.insert(0, "source_row", range(1, len(df) + 1))
    cleaned, _ = clean_dataframe(df)
    dd = find_duplicates(cleaned)
    issues = validate_records(dd.kept, dd.removed, dd.potential_pairs)
    return add_quality_flags(dd.kept, issues), issues


def test_complete_valid_record_has_no_issues_but_is_not_called_verified():
    kept, issues = _run([["A Clinic", "Dr. X", "Cardiology", "Pune", "98765 55501",
                          "https://a.example.com", "https://src.example.org/a"]])
    assert issues.empty
    assert not kept["is_incomplete"].iloc[0]
    assert kept["verification_status"].iloc[0] == VERIFICATION_LABEL
    assert "verified" not in kept["verification_status"].iloc[0].lower().replace("not verified", "")


def test_missing_required_field_marks_incomplete_and_flagged():
    kept, issues = _run([["A Clinic", None, "Cardiology", None, "98765 55501", None, None]])
    assert kept["is_incomplete"].iloc[0]
    assert kept["needs_review"].iloc[0]
    assert ("city", "missing_value") in set(zip(issues["field"], issues["issue_type"]))


def test_missing_optional_doctor_alone_does_not_flag_record():
    kept, _ = _run([["A Clinic", None, "Cardiology", "Pune", "98765 55501",
                     "https://a.example.com", "https://src.example.org/a"]])
    assert not kept["is_incomplete"].iloc[0]
    assert not kept["needs_review"].iloc[0]


def test_invalid_phone_and_website_are_reported():
    _, issues = _run([["A Clinic", "Dr X", "Dental", "Pune", "12345", "not a website",
                       "https://src.example.org/a"]])
    types = set(issues["issue_type"])
    assert {"invalid_phone", "invalid_website"} <= types


def test_every_issue_row_is_labelled_unverified():
    _, issues = _run([["A Clinic", None, None, None, "12345", "bad url", None]])
    assert (issues["verification_status"] == VERIFICATION_LABEL).all()


def test_exact_duplicate_is_reported_as_info():
    _, issues = _run([
        ["A Clinic", None, "GP", "Pune", "98765 55501", None, None],
        ["a clinic", None, "GP", "Pune", "98765 55501", None, None],
    ])
    row = issues[issues["issue_type"] == "exact_duplicate"].iloc[0]
    assert row["severity"] == "info" and row["source_row"] == 2
