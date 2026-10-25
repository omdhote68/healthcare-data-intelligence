"""Tests for src/dedupe.py."""

import pandas as pd

from src.cleaner import clean_dataframe
from src.dedupe import find_duplicates


def _prepare(rows):
    df = pd.DataFrame(rows, columns=["practice_name", "doctor_name", "specialty", "city",
                                     "phone", "website", "source_url"])
    df.insert(0, "source_row", range(1, len(df) + 1))
    cleaned, _ = clean_dataframe(df)
    return cleaned


def test_exact_duplicates_after_cleaning_are_removed():
    cleaned = _prepare([
        ["Green Clinic", None, "GP", "Pune", "+91 98765 55501", None, None],
        ["  green clinic ", None, "gp", "pune", "98765-55501", None, None],
    ])
    result = find_duplicates(cleaned)
    assert len(result.kept) == 1
    assert len(result.removed) == 1
    assert result.removed["duplicate_of_row"].iloc[0] == 1


def test_similar_names_same_phone_are_flagged_not_removed():
    cleaned = _prepare([
        ["Sunrise Heart Centre", None, "Cardiology", "Mumbai", "022 5550 1234", None, None],
        ["Sunrise Heart Center", None, "Cardiology", "Mumbai", "022 5550 1234", None, None],
    ])
    result = find_duplicates(cleaned)
    assert len(result.kept) == 2
    assert len(result.removed) == 0
    assert len(result.potential_pairs) == 1


def test_different_practices_are_not_flagged():
    cleaned = _prepare([
        ["Alpha Dental", None, "Dentistry", "Pune", "98765 11111", None, None],
        ["Zenith Eye Care", None, "Eye", "Pune", "98765 22222", None, None],
    ])
    result = find_duplicates(cleaned)
    assert len(result.kept) == 2 and len(result.potential_pairs) == 0


def test_same_name_with_no_city_or_phone_is_not_auto_removed():
    cleaned = _prepare([
        ["Mystery Clinic", None, None, None, None, None, None],
        ["Mystery Clinic", None, None, None, None, None, None],
    ])
    result = find_duplicates(cleaned)
    assert len(result.kept) == 2        # too little information to delete safely


def test_invalid_phones_do_not_cause_false_matches():
    cleaned = _prepare([
        ["Alpha Dental", None, None, "Pune", "12345", None, None],
        ["Zenith Eye Care", None, None, "Mumbai", "12345", None, None],
    ])
    assert len(find_duplicates(cleaned).potential_pairs) == 0
