"""Data-quality checks.

Everything here is DETECTION, not VERIFICATION:
  * "invalid_phone" means the number looks wrong.
  * A record with no issues has only passed FORMAT checks. Nobody has confirmed
    that the practice, phone number or website is real or current.
"""

import pandas as pd

from src.config import REQUIRED_FOR_COMPLETE, VERIFICATION_LABEL

ISSUE_COLUMNS = [
    "source_row", "practice_name", "field", "issue_type",
    "severity", "detail", "verification_status",
]

FIELD_LABELS = {
    "practice_name": "practice name", "doctor_name": "doctor name",
    "specialty": "specialty", "city": "city", "phone": "phone number",
    "website": "website", "source_url": "source URL",
}

# severity for a missing value, by field
MISSING_SEVERITY = {
    "practice_name": "high", "specialty": "medium", "city": "medium",
    "phone": "medium", "source_url": "medium", "doctor_name": "low", "website": "low",
}


def _issue(row, field, issue_type, severity, detail):
    return {
        "source_row": row["source_row"], "practice_name": row.get("practice_name"),
        "field": field, "issue_type": issue_type, "severity": severity,
        "detail": detail, "verification_status": VERIFICATION_LABEL,
    }


def validate_records(kept: pd.DataFrame, removed: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    """Return one row per detected issue."""
    issues = []

    for _, row in kept.iterrows():
        # Missing values
        for field in MISSING_SEVERITY:
            if pd.isna(row[field]) or row[field] is None:
                label = FIELD_LABELS[field]
                issues.append(_issue(row, field, "missing_value", MISSING_SEVERITY[field],
                                     f"No {label} was provided."))
        # Format problems
        if row["phone_status"] == "invalid":
            issues.append(_issue(row, "phone", "invalid_phone", "medium",
                                 f"Phone number '{row['phone']}' has an unusual format or length."))
        if row["website_status"] == "invalid":
            issues.append(_issue(row, "website", "invalid_website", "medium",
                                 f"Website '{row['website']}' is not a well-formed web address."))
        if row["source_url_status"] == "invalid":
            issues.append(_issue(row, "source_url", "invalid_source_url", "medium",
                                 f"Source URL '{row['source_url']}' is not a well-formed web address."))

    # Potential duplicates: flag both rows of every pair
    by_row = kept.set_index("source_row", drop=False)
    for _, pair in pairs.iterrows():
        for mine, other in ((pair["source_row_a"], pair["source_row_b"]),
                            (pair["source_row_b"], pair["source_row_a"])):
            if mine in by_row.index:
                issues.append(_issue(
                    by_row.loc[mine], "record", "potential_duplicate", "medium",
                    f"May duplicate row {other} ({pair['reason']}). Needs human review; not removed.",
                ))

    # Exact duplicates that were removed
    for _, row in removed.iterrows():
        issues.append(_issue(row, "record", "exact_duplicate", "info",
                             f"Removed: identical to row {row['duplicate_of_row']} after cleaning."))

    return pd.DataFrame(issues, columns=ISSUE_COLUMNS)


def add_quality_flags(kept: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    """Add per-record flag columns to the kept records."""
    out = kept.copy()
    out["is_incomplete"] = out[REQUIRED_FOR_COMPLETE].isna().any(axis=1)

    relevant = issues[issues["issue_type"] != "exact_duplicate"]
    counts = relevant.groupby("source_row").size()
    serious = relevant[relevant["severity"].isin(["high", "medium"])].groupby("source_row").size()
    flags = relevant.groupby("source_row")["issue_type"].apply(lambda s: ", ".join(sorted(set(s))))

    out["issue_count"] = out["source_row"].map(counts).fillna(0).astype(int)
    out["needs_review"] = out["source_row"].map(serious).fillna(0).astype(int) > 0
    out["quality_flags"] = out["source_row"].map(flags).fillna("")
    out["verification_status"] = VERIFICATION_LABEL
    return out
