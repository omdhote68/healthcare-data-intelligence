"""Streamlit dashboard for the Healthcare Data Intelligence & Automation project.

Run with:  streamlit run app.py
All real work happens in src/pipeline.py; this file only handles what the user sees.
"""

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # reads ANTHROPIC_API_KEY from a local .env file if present

from src.ai_analysis import ai_available, cache_ai_caller, get_ai_caller  # noqa: E402
from src.config import SAMPLE_FILE, SEVERITY_ORDER  # noqa: E402
from src.exporter import (  # noqa: E402
    cleaned_for_export, to_csv_bytes, to_excel_bytes, workbook_sheets,
)
from src.loader import LoaderError  # noqa: E402
from src.logger import get_logger  # noqa: E402
from src.pipeline import run_pipeline  # noqa: E402

logger = get_logger()

st.set_page_config(page_title="Healthcare Data Intelligence", page_icon="🩺", layout="wide")

# ---------------------------------------------------------------- header
st.title("🩺 Healthcare Data Intelligence & Automation")
st.caption(
    "Upload a healthcare practice directory file. The tool cleans it, finds data-quality "
    "problems, and exports a cleaned file plus a quality report."
)
st.info(
    "**Detected is not verified.** All checks here are automated format checks. "
    "A record that passes has NOT been confirmed as real or accurate - that needs a human "
    "and a trusted external source. Missing information is never guessed."
)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("1. Choose data")
    source_choice = st.radio("Data source", ["Upload a file", "Use sample data"])
    uploaded = None
    if source_choice == "Upload a file":
        uploaded = st.file_uploader("CSV or Excel file", type=["csv", "xlsx"])
    else:
        st.caption("Uses the built-in fictional sample file (11 made-up records).")

    st.header("2. Options")
    ai_ok = ai_available()
    use_ai = st.checkbox(
        "Use AI analysis",
        value=False,
        disabled=not ai_ok,
        help="Uses an AI API to classify records the keyword rules could not, and to write "
             "the summary and explanations. All AI output is validated before use.",
    )
    if ai_ok:
        st.caption("AI key found. Only specialty/practice names and aggregate counts are sent.")
    else:
        st.caption("No API key found, so rule-based mode is used. Everything still works.")

    st.header("3. Run")
    run_clicked = st.button("Process data", type="primary")

# ---------------------------------------------------------------- run pipeline
if run_clicked:
    if source_choice == "Upload a file" and uploaded is None:
        st.warning("Please choose a CSV or Excel file first.")
    else:
        try:
            ai_caller = get_ai_caller() if use_ai else None
            if ai_caller is not None:
                response_cache = st.session_state.setdefault("_gemini_response_cache", {})
                ai_caller = cache_ai_caller(ai_caller, response_cache)
            with st.spinner("Cleaning and analysing your data..."):
                if source_choice == "Use sample data":
                    result = run_pipeline(SAMPLE_FILE, use_ai=use_ai, ai_caller=ai_caller)
                    label = "sample_practices.csv (fictional sample)"
                else:
                    result = run_pipeline(
                        uploaded, filename=uploaded.name, use_ai=use_ai, ai_caller=ai_caller
                    )
                    label = uploaded.name
            st.session_state["result"] = result
            st.session_state["label"] = label
        except LoaderError as exc:
            st.session_state.pop("result", None)
            st.error(f"Could not process this file: {exc}")
        except Exception:  # noqa: BLE001
            st.session_state.pop("result", None)
            logger.exception("Unexpected pipeline failure")
            st.error("Something unexpected went wrong. Details were saved to logs/pipeline.log.")

result = st.session_state.get("result")
if result is None:
    st.write("👈 Choose a data source in the sidebar, then click **Process data**.")
    st.stop()

# ---------------------------------------------------------------- results
m = result.metrics
st.subheader(f"Results for: {st.session_state.get('label', '')}")

cols = st.columns(6)
cols[0].metric("Imported", m["imported"])
cols[1].metric("Duplicates removed", m["duplicates_removed"])
cols[2].metric("Cleaned records", m["cleaned"])
cols[3].metric("Incomplete", m["incomplete"])
cols[4].metric("Flagged for review", m["flagged"])
cols[5].metric("Possible duplicates", m["potential_duplicate_records"])
st.caption(
    "Flagged = records with at least one medium/high-severity issue. "
    "Possible duplicates are kept in the data and need a human decision."
)

for note in result.notes:
    st.warning(note)

tabs = st.tabs([
    "Cleaned data", "Issue report", "Duplicates", "AI / Summary",
    "Column mapping", "Change log", "Downloads",
])

# --- Cleaned data
with tabs[0]:
    st.write("Cleaned records (original phone/website values are kept in their own columns).")
    only_review = st.checkbox("Show only records that need review")
    table = cleaned_for_export(result.cleaned)
    if only_review:
        table = table[table["needs_review"]]
    st.dataframe(table)

# --- Issue report
with tabs[1]:
    issues = result.issues
    if issues.empty:
        st.success("No format problems were detected. This does not mean the data is verified.")
    else:
        severities = [s for s in SEVERITY_ORDER if s in set(issues["severity"])]
        chosen = st.multiselect("Severity", severities, default=severities)
        st.dataframe(issues[issues["severity"].isin(chosen)])
        st.write("**Issues by type**")
        st.bar_chart(issues["issue_type"].value_counts())

# --- Duplicates
with tabs[2]:
    st.write("**Exact duplicates removed** (the first copy was kept)")
    if result.removed_duplicates.empty:
        st.write("None found.")
    else:
        st.dataframe(result.removed_duplicates[
            ["source_row", "practice_name", "city", "phone", "duplicate_of_row"]])
    st.write("**Potential duplicates - kept, needs human review**")
    if result.potential_pairs.empty:
        st.write("None found.")
    else:
        st.dataframe(result.potential_pairs)

# --- AI / summary
with tabs[3]:
    ai = result.ai
    st.write(f"**Analysis mode:** {ai.mode}")
    if ai.mode == "rule-based":
        st.caption("Keyword rules and templates were used. The AI API was not used for this run.")
    for warning in ai.warnings:
        st.warning(warning)
    st.write("**Dataset summary**")
    st.write(ai.summary)
    if ai.recommendations:
        st.write("**Suggested next steps**")
        for rec in ai.recommendations:
            st.write(f"- {rec}")
    st.write("**Specialty categories**")
    st.bar_chart(ai.categories["specialty_category"].value_counts())
    st.write("**What the issues mean**")
    st.dataframe(ai.explanations)

# --- Column mapping
with tabs[4]:
    mapping = pd.DataFrame(
        [{"standard column": k, "your file's column": v} for k, v in result.load.column_mapping.items()]
    )
    st.dataframe(mapping)
    if result.load.missing_standard_columns:
        st.write("Not found (left empty): " + ", ".join(result.load.missing_standard_columns))
    if result.load.ignored_columns:
        st.write("Ignored columns: " + ", ".join(result.load.ignored_columns))

# --- Change log
with tabs[5]:
    st.write("Every value the cleaner changed, with its original, for auditing.")
    st.dataframe(result.changes)

# --- Downloads
with tabs[6]:
    st.write("Download the results:")
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇ Cleaned data (CSV)", to_csv_bytes(cleaned_for_export(result.cleaned)),
                       file_name="cleaned_data.csv", mime="text/csv")
    c2.download_button("⬇ Data-quality report (CSV)", to_csv_bytes(result.issues),
                       file_name="data_quality_report.csv", mime="text/csv")
    c3.download_button(
        "⬇ Full workbook (Excel)", to_excel_bytes(workbook_sheets(result)),
        file_name="healthcare_data_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
