"""Tests for src/cleaner.py."""

import pandas as pd

from src.cleaner import clean_dataframe, clean_phone, clean_text, clean_url, match_key, smart_title


def test_clean_text_trims_and_collapses_whitespace():
    assert clean_text("  Hello    World \n") == "Hello World"


def test_clean_text_turns_placeholders_into_none():
    for value in [None, "", "   ", "N/A", "nan", "null", "-"]:
        assert clean_text(value) is None


def test_smart_title_fixes_case_but_keeps_apostrophes_and_acronyms():
    assert smart_title("greenfield family clinic") == "Greenfield Family Clinic"
    assert smart_title("riverbend children's hospital") == "Riverbend Children's Hospital"
    assert smart_title("Dr. A. Sample") == "Dr. A. Sample"
    assert smart_title("SUNRISE HEART CENTRE") == "Sunrise Heart Centre"
    assert smart_title("City ENT Clinic") == "City ENT Clinic"
    assert smart_title(None) is None


def test_match_key_ignores_case_punctuation_and_spaces():
    assert match_key("  Sunrise  Heart-Centre! ") == "sunrise heart centre"
    assert match_key(None) == ""


def test_phone_indian_mobile_with_country_code():
    cleaned, key, status = clean_phone("+91 98765 55501")
    assert (cleaned, key, status) == ("+91 98765 55501", "9876555501", "ok")


def test_phone_formats_with_dashes_match_same_key():
    assert clean_phone("98765-55501")[0] == "98765 55501"
    assert clean_phone("98765-55501")[1] == clean_phone("+91 98765 55501")[1]


def test_phone_does_not_invent_digits():
    cleaned, _, _ = clean_phone("(022) 5550 1234")
    assert cleaned == "02255501234"        # same digits, only formatting removed


def test_phone_leading_zero_kept():
    assert clean_phone("0712 555 0042")[0] == "07125550042"


def test_phone_too_short_is_invalid_and_kept_as_text():
    cleaned, key, status = clean_phone("12345")
    assert status == "invalid" and cleaned == "12345" and key == ""


def test_phone_with_letters_or_repeated_digit_is_invalid():
    assert clean_phone("call us")[2] == "invalid"
    assert clean_phone("0000000000")[2] == "invalid"


def test_phone_missing():
    assert clean_phone(None) == (None, "", "missing")
    assert clean_phone("  ")[2] == "missing"


def test_url_adds_https_when_missing_and_reports_it():
    cleaned, status, added = clean_url("www.example.com")
    assert (cleaned, status, added) == ("https://www.example.com", "ok", True)


def test_url_valid_unchanged():
    assert clean_url("https://example.org/a") == ("https://example.org/a", "ok", False)


def test_url_invalid_cases():
    for bad in ["not a website", "htp:/bright-smile", "https://nodot", "ftp://example.com", "http://"]:
        assert clean_url(bad)[1] == "invalid", bad


def test_url_missing():
    assert clean_url(None)[1] == "missing"


def test_clean_dataframe_keeps_originals_and_logs_changes():
    df = pd.DataFrame({
        "source_row": [1],
        "practice_name": ["  greenfield clinic "], "doctor_name": [None],
        "specialty": ["general practice"], "city": ["pune"],
        "phone": ["98765-55501"], "website": ["example.com"], "source_url": [None],
    })
    cleaned, changes = clean_dataframe(df)

    assert cleaned["practice_name"].iloc[0] == "Greenfield Clinic"
    assert cleaned["phone_original"].iloc[0] == "98765-55501"
    assert cleaned["website_original"].iloc[0] == "example.com"
    assert cleaned["source_url_status"].iloc[0] == "missing"
    assert "practice_name" in set(changes["field"])
    assert "doctor_name" not in set(changes["field"])      # None -> None is not a change
