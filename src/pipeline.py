"""The automated pipeline: import -> clean -> validate -> (optional AI) -> results.

One function, `run_pipeline`, does everything. The Streamlit app and the command-line
script both call it, so behaviour is identical in both.
"""

from dataclasses import dataclass, field

import pandas as pd

from src.ai_analysis import AIResult, run_ai_analysis
from src.cleaner import clean_dataframe
from src.dedupe import find_duplicates
from src.loader import LoadResult, load_file
from src.logger import get_logger
from src.validator import add_quality_flags, validate_records

logger = get_logger()


@dataclass
class PipelineResult:
    load: LoadResult
    cleaned: pd.DataFrame            # kept records with flags + categories
    removed_duplicates: pd.DataFrame
    potential_pairs: pd.DataFrame
    issues: pd.DataFrame             # the data-quality report
    changes: pd.DataFrame            # audit log of every changed value
    metrics: dict
    ai: AIResult
    notes: list = field(default_factory=list)


def run_pipeline(source, filename: str = None, use_ai: bool = False, ai_caller=None) -> PipelineResult:
    """Run the full pipeline. Raises LoaderError (friendly message) if the file is unusable."""
    logger.info("=== Pipeline started ===")

    # 1. Import
    load = load_file(source, filename)

    # 2. Clean
    cleaned_all, changes = clean_dataframe(load.data)

    # 3. Duplicates + validation
    dedupe = find_duplicates(cleaned_all)
    issues = validate_records(dedupe.kept, dedupe.removed, dedupe.potential_pairs)
    kept = add_quality_flags(dedupe.kept, issues)

    # 4. Metrics (computed before AI so the summary uses real numbers)
    flagged_pairs = set(dedupe.potential_pairs["source_row_a"]) | set(dedupe.potential_pairs["source_row_b"])
    metrics = {
        "imported": int(len(load.data)),
        "blank_rows_dropped": int(load.empty_rows_dropped),
        "duplicates_removed": int(len(dedupe.removed)),
        "cleaned": int(len(kept)),
        "incomplete": int(kept["is_incomplete"].sum()),
        "flagged": int(kept["needs_review"].sum()),
        "potential_duplicate_records": int(len(flagged_pairs)),
        "invalid_phone": int((kept["phone_status"] == "invalid").sum()),
        "invalid_website": int((kept["website_status"] == "invalid").sum()),
        "issues_total": int(len(issues[issues["issue_type"] != "exact_duplicate"])),
    }

    # 5. Categorise + summarise (rule-based always; AI optional)
    ai = run_ai_analysis(kept, issues, metrics, use_ai=use_ai, caller=ai_caller)
    kept = kept.merge(ai.categories, on="source_row", how="left")

    notes = []
    if load.missing_standard_columns:
        notes.append("Columns not found in the file (left empty, nothing invented): "
                     + ", ".join(load.missing_standard_columns))
    if load.ignored_columns:
        notes.append("Columns in the file that were ignored: " + ", ".join(load.ignored_columns))

    logger.info("=== Pipeline finished: %s ===", metrics)
    return PipelineResult(load, kept, dedupe.removed, dedupe.potential_pairs, issues,
                          changes, metrics, ai, notes)
