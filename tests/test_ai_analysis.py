"""Tests for src/ai_analysis.py. A fake 'AI' function is used, so no API key is needed."""

import json

import pandas as pd
import pytest

from src.ai_analysis import (
    CATEGORIES, classify_rules, parse_json_response, run_ai_analysis,
    validate_categories, validate_explanations, validate_summary,
)


def test_rules_use_specialty_first():
    assert classify_rules("Paediatrics", "Anything")[0] == "Pediatrics"
    assert classify_rules("Orthopaedics", "X")[0] == "Orthopedics"
    assert classify_rules("General Practice", "X")[0] == "General Practice"


def test_rules_fall_back_to_practice_name():
    category, source = classify_rules(None, "Bright Smile Dental")
    assert category == "Dentistry" and "practice name" in source


def test_rules_say_unknown_instead_of_guessing():
    assert classify_rules(None, "Wellness First Clinic")[0] == "Unknown"
    assert classify_rules(None, "Greenfield Family Clinic")[0] == "Unknown"   # GP not inferred from name


def test_rules_mark_unrecognised_specialty_as_other():
    assert classify_rules("Sleep Medicine", "Night Clinic")[0] == "Other"


def test_parse_json_handles_code_fences():
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_response('Here you go: {"a": 1} thanks') == {"a": 1}


def test_parse_json_rejects_garbage():
    with pytest.raises(ValueError):
        parse_json_response("no json here")


def test_validate_categories_drops_invalid_entries():
    payload = {"items": [
        {"id": 0, "category": "Cardiology"},
        {"id": 1, "category": "Made Up Category"},     # not allowed
        {"id": 99, "category": "Neurology"},           # unknown id
        "junk",
    ]}
    assert validate_categories(payload, {0, 1}) == {0: "Cardiology"}


def test_validate_summary_rejects_invented_numbers():
    ok = {"summary": "There are 10 records and 3 are incomplete in this file.", "recommendations": []}
    assert validate_summary(ok, {10, 3})[0].startswith("There are 10")
    with pytest.raises(ValueError):
        validate_summary(ok, {10})          # "3" was never provided


def test_validate_summary_rejects_bad_structure():
    with pytest.raises(ValueError):
        validate_summary({"summary": "short"}, set())
    with pytest.raises(ValueError):
        validate_summary(["not", "a", "dict"], set())


def test_validate_explanations_keeps_only_known_issue_types():
    payload = {"explanations": {"invalid_phone": "The phone number looks wrong; check the source.",
                                "invented_type": "This should be ignored by the validator."}}
    assert list(validate_explanations(payload, {"invalid_phone"})) == ["invalid_phone"]


# ---- full run with a fake AI -------------------------------------------------
def _fixture():
    kept = pd.DataFrame({
        "source_row": [1, 2],
        "practice_name": ["Wellness First Clinic", "Sleep Easy Centre"],
        "specialty": [None, "Sleep Medicine"],
    })
    issues = pd.DataFrame({"issue_type": ["missing_value"], "source_row": [1]})
    metrics = {"imported": 2, "cleaned": 2, "duplicates_removed": 0, "incomplete": 1, "flagged": 1,
               "potential_duplicate_records": 0, "invalid_phone": 0, "invalid_website": 0}
    return kept, issues, metrics


def test_run_without_ai_is_rule_based():
    kept, issues, metrics = _fixture()
    result = run_ai_analysis(kept, issues, metrics, use_ai=False)
    assert result.mode == "rule-based"
    assert set(result.categories["specialty_category"]) <= set(CATEGORIES)
    assert "not been verified" in result.summary or "not verified" in result.summary.lower() \
        or "no record has been verified" in result.summary


def test_run_with_good_fake_ai_uses_validated_answers():
    kept, issues, metrics = _fixture()

    def fake(system, prompt):
        if "Classify" in prompt:
            return json.dumps({"items": [{"id": 0, "category": "Unknown"}, {"id": 1, "category": "Other"}]})
        if "summary" in prompt.lower() and "Facts" in prompt:
            return json.dumps({"summary": "Two records were imported and none have been externally verified.",
                               "recommendations": ["Fill in the missing field."]})
        return json.dumps({"explanations": {"missing_value": "A required field is empty; look it up from a trusted source."}})

    result = run_ai_analysis(kept, issues, metrics, use_ai=True, caller=fake)
    assert result.mode == "ai"
    assert result.summary.startswith("Two records")
    assert result.explanations["source"].iloc[0] == "ai (validated)"


def test_run_with_bad_ai_output_falls_back_safely():
    kept, issues, metrics = _fixture()

    def bad(system, prompt):
        return "Sorry, I cannot do that."           # not JSON at all

    result = run_ai_analysis(kept, issues, metrics, use_ai=True, caller=bad)
    assert result.mode == "ai (with fallbacks)"
    assert result.warnings
    assert result.summary                              # template summary still produced
    assert result.explanations["source"].iloc[0] == "template"


def test_ai_that_invents_a_category_is_ignored():
    kept, issues, metrics = _fixture()

    def sneaky(system, prompt):
        if "Classify" in prompt:
            return json.dumps({"items": [{"id": 0, "category": "Brain Surgery Centre"}]})
        return "nope"

    result = run_ai_analysis(kept, issues, metrics, use_ai=True, caller=sneaky)
    assert "Brain Surgery Centre" not in set(result.categories["specialty_category"])


def test_ai_requested_without_key_falls_back(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    kept, issues, metrics = _fixture()
    result = run_ai_analysis(kept, issues, metrics, use_ai=True)
    assert result.mode == "rule-based"
    assert any("no API key" in w for w in result.warnings)
