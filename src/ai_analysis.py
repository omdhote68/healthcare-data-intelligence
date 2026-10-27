"""AI-assisted analysis, with a full non-AI fallback.

What needs an AI API (and an API key)?
  * Categorising records the keyword rules could not classify
  * A written dataset summary and recommendations
  * Plain-English explanations of each issue type
Without a key, rule-based/template versions are used instead and clearly labelled.

Safety rules for AI output:
  * The AI only sees the minimum it needs (specialty + practice name, or aggregate counts).
  * It must reply in JSON. We parse it and VALIDATE it. Anything that fails validation
    is discarded and replaced by the rule-based result.
  * AI never decides whether a record is correct; it only labels and describes.
"""

import json
import os
import re
from dataclasses import dataclass, field

import pandas as pd

from src.config import MAX_AI_ITEMS
from src.logger import get_logger

logger = get_logger()

CATEGORIES = [
    "General Practice", "Cardiology", "Dermatology", "Pediatrics", "Orthopedics",
    "Dentistry", "Ophthalmology", "Neurology", "ENT", "Gynecology",
    "Psychiatry", "Oncology", "Other", "Unknown",
]
# "Other"   = a specialty is stated but is not in our list
# "Unknown" = not enough information to say

SPECIALTY_PATTERNS = {
    "General Practice": [r"general (practi|physician|medicine)", r"family (medicine|physician|practice)",
                         r"primary care", r"\bgp\b"],
    "Cardiology": [r"cardio", r"\bheart\b"],
    "Dermatology": [r"dermat", r"\bskin\b"],
    "Pediatrics": [r"p(a)?ediatric", r"\bchild", r"\bkids?\b"],
    "Orthopedics": [r"orthop", r"\bortho\b", r"\bbone\b", r"\bspine\b", r"\bjoint\b"],
    "Dentistry": [r"dental", r"dentist", r"\bteeth\b"],
    "Ophthalmology": [r"ophthal", r"\beye\b"],
    "Neurology": [r"neuro", r"\bbrain\b"],
    "ENT": [r"\bent\b", r"otolaryng", r"ear,? nose"],
    "Gynecology": [r"gyn(a)?e", r"obstet", r"maternity"],
    "Psychiatry": [r"psychiat", r"psycholog", r"mental health"],
    "Oncology": [r"oncolog", r"\bcancer\b"],
}
# General Practice wording is too ambiguous to infer from a practice NAME.
NAME_EXCLUDED = {"General Practice"}

ISSUE_EXPLANATIONS = {
    "missing_value": "A field that should normally be filled in is empty. The tool does not guess "
                     "missing values - someone needs to find them from a trusted source.",
    "invalid_phone": "The phone number has an unusual length, contains letters, or repeats one digit. "
                     "It may be a typing error or a placeholder. Check it against the original source.",
    "invalid_website": "The website text is not a well-formed web address (for example it has spaces "
                       "or a broken prefix). It may be a typo; the correct address must be looked up.",
    "invalid_source_url": "The source link is not a well-formed web address, so the origin of this "
                          "record cannot be traced from it.",
    "potential_duplicate": "Another record shares the same phone number or has a very similar name in "
                           "the same city. It may be the same practice entered twice, or two real "
                           "branches. These were NOT removed - a person should review them.",
    "exact_duplicate": "This record became identical to an earlier one after cleaning (same name, "
                       "city and phone), so the later copy was removed. It is listed for transparency.",
}


# --------------------------------------------------------------------------
# Rule-based categorisation (no API needed)
# --------------------------------------------------------------------------
def _match_category(text: str, skip=()):
    text = (text or "").lower()
    for category, patterns in SPECIALTY_PATTERNS.items():
        if category in skip:
            continue
        if any(re.search(p, text) for p in patterns):
            return category
    return None


def classify_rules(specialty, practice_name):
    """Return (category, source). Specialty text is tried first, then the practice name."""
    specialty = None if specialty is None or pd.isna(specialty) else str(specialty)
    practice_name = None if practice_name is None or pd.isna(practice_name) else str(practice_name)

    if specialty:
        category = _match_category(specialty)
        if category:
            return category, "rule (specialty)"
    category = _match_category(practice_name, skip=NAME_EXCLUDED)
    if category:
        return category, "rule (practice name)"
    if specialty:
        return "Other", "rule (specialty not in list)"
    return "Unknown", "rule (no information)"


# --------------------------------------------------------------------------
# AI plumbing
# --------------------------------------------------------------------------

def get_ai_caller():
    """Return a Gemini API caller, or None if AI is not configured."""
    key = os.getenv("GEMINI_API_KEY", "").strip()

    # Read the key from Streamlit Cloud Secrets if needed.
    if not key:
        try:
            import streamlit as st
            key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
        except Exception:
            key = ""

    if not key:
        return None

    try:
        from google import genai
    except ImportError:
        logger.warning(
            "Gemini key is configured, but google-genai is not installed."
        )
        return None

    try:
        client = genai.Client(api_key=key)
    except Exception as exc:
        logger.warning("Could not initialise Gemini client: %s", exc)
        return None

    model = os.getenv("GEMINI_MODEL", "").strip()
    if model.removeprefix("models/") == "gemini-2.5-flash":
        model = "gemini-3.8-flash"
    model = model or "gemini-3.8-flash"

    def call(system: str, prompt: str) -> str:
        response = client.models.generate_content(
            model=model,
            contents=f"{system}\n\n{prompt}",
        )
        text = getattr(response, "text", None)
        if not text:
            raise ValueError("Gemini returned an empty response.")
        return text

    return call



def ai_available() -> bool:
    return get_ai_caller() is not None


def parse_json_response(text: str):
    """Extract a JSON object/array from model text (handles ```json fences)."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(opener), cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("Response did not contain valid JSON.")


SYSTEM_PROMPT = (
    "You help clean a healthcare practice directory. Reply with JSON only - no commentary, "
    "no markdown. Never invent facts, names, phone numbers or numbers. If information is "
    "insufficient, say so. You cannot verify whether any practice is real or accurate."
)


def validate_categories(payload, expected_ids):
    """Return {id: category} containing only valid entries."""
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("Expected a list of items.")
    valid = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id, category = item.get("id"), item.get("category")
        if item_id in expected_ids and category in CATEGORIES:
            valid[item_id] = category
    return valid


def validate_summary(payload, allowed_numbers):
    """Check structure, length, and that every number mentioned was supplied by us."""
    if not isinstance(payload, dict):
        raise ValueError("Summary must be a JSON object.")
    summary = payload.get("summary")
    recs = payload.get("recommendations", [])
    if not isinstance(summary, str) or not (20 <= len(summary) <= 1200):
        raise ValueError("Summary text missing or wrong length.")
    if not isinstance(recs, list) or len(recs) > 6 or not all(isinstance(r, str) and r for r in recs):
        raise ValueError("Recommendations must be a short list of strings.")
    mentioned = {int(n) for n in re.findall(r"\d+", summary + " " + " ".join(recs))}
    unknown = mentioned - allowed_numbers
    if unknown:
        raise ValueError(f"Summary mentions numbers that were not provided: {sorted(unknown)}")
    return summary.strip(), [r.strip() for r in recs]


def validate_explanations(payload, issue_types):
    if not isinstance(payload, dict) or not isinstance(payload.get("explanations"), dict):
        raise ValueError("Expected {'explanations': {...}}.")
    valid = {}
    for key, text in payload["explanations"].items():
        if key in issue_types and isinstance(text, str) and 10 <= len(text) <= 500:
            valid[key] = text.strip()
    return valid


# --------------------------------------------------------------------------
# Result object and main entry point
# --------------------------------------------------------------------------
@dataclass
class AIResult:
    mode: str = "rule-based"          # "rule-based", "ai", or "ai (with fallbacks)"
    categories: pd.DataFrame = None   # source_row, specialty_category, category_source
    summary: str = ""
    recommendations: list = field(default_factory=list)
    explanations: pd.DataFrame = None  # issue_type, count, explanation, source
    warnings: list = field(default_factory=list)


def _template_summary(metrics, category_counts, issue_counts):
    top = ", ".join(f"{name} ({count})" for name, count in category_counts.head(3).items())
    text = (
        f"The file contained {metrics['imported']} records. After cleaning, {metrics['cleaned']} remain "
        f"({metrics['duplicates_removed']} exact duplicate(s) removed). "
        f"{metrics['incomplete']} record(s) are incomplete and {metrics['flagged']} need review. "
    )
    if top:
        text += f"Most common categories: {top}. "
    text += "These are automated format checks only; no record has been verified against an external source."
    recs = []
    if metrics["incomplete"]:
        recs.append("Fill in missing required fields from a trusted source.")
    if metrics["potential_duplicate_records"]:
        recs.append("Review the potential duplicate pairs and merge or keep them manually.")
    if metrics["invalid_phone"] or metrics["invalid_website"]:
        recs.append("Re-check invalid phone numbers and websites against the original source.")
    return text, recs


def run_ai_analysis(kept, issues, metrics, use_ai=False, caller=None) -> AIResult:
    """Categorise records, summarise the dataset, explain issues.

    use_ai=False  -> rules and templates only.
    use_ai=True   -> try the AI for each task; fall back per task if it fails validation.
    `caller` can be supplied (e.g. in tests); otherwise the real API is used if configured.
    """
    result = AIResult()

    # 1) Rule-based categories for everyone
    rule_rows = [classify_rules(s, n) for s, n in zip(kept["specialty"], kept["practice_name"])]
    categories = pd.DataFrame({
        "source_row": kept["source_row"].values,
        "specialty_category": [r[0] for r in rule_rows],
        "category_source": [r[1] for r in rule_rows],
    })

    issue_counts = issues[issues["issue_type"] != "exact_duplicate"]["issue_type"].value_counts()
    all_issue_counts = issues["issue_type"].value_counts()

    if use_ai and caller is None:
        caller = get_ai_caller()
        if caller is None:
            result.warnings.append("AI was requested but no API key/package is available; "
                                   "rule-based results were used instead.")
    ai_on = use_ai and caller is not None
    fallbacks = 0

    # 2) AI categorisation for records the rules could not place
    if ai_on:
        unresolved = categories[categories["specialty_category"].isin(["Other", "Unknown"])]
        pairs = {}
        for idx in unresolved.index:
            key = (kept.at[idx, "specialty"], kept.at[idx, "practice_name"])
            key = tuple(None if pd.isna(v) else v for v in key)
            pairs.setdefault(key, []).append(idx)
        keys = list(pairs)[:MAX_AI_ITEMS]
        if keys:
            items = [{"id": i, "specialty": k[0], "practice_name": k[1]} for i, k in enumerate(keys)]
            prompt = (
                "Classify each record into exactly one category from this list: "
                f"{CATEGORIES}.\nUse 'Unknown' if the specialty/name gives too little information; "
                "use 'Other' if a specialty is stated but fits none of the categories. Do not guess.\n"
                'Reply as JSON: {"items": [{"id": <number>, "category": "<category>"}]}\n'
                f"Records: {json.dumps(items)}"
            )
            try:
                valid = validate_categories(parse_json_response(caller(SYSTEM_PROMPT, prompt)),
                                            set(range(len(keys))))
                for item_id, category in valid.items():
                    for idx in pairs[keys[item_id]]:
                        categories.at[idx, "specialty_category"] = category
                        categories.at[idx, "category_source"] = "ai (validated)"
                if len(valid) < len(keys):
                    fallbacks += 1
                    result.warnings.append("Some AI category answers were invalid and were ignored.")
            except Exception as exc:  # noqa: BLE001
                fallbacks += 1
                logger.warning("AI categorisation failed: %s", exc)
                result.warnings.append(f"AI categorisation failed ({exc}); rule-based categories kept.")
    result.categories = categories

    category_counts = categories["specialty_category"].value_counts()

    # 3) Summary
    summary, recs = _template_summary(metrics, category_counts, all_issue_counts)
    if ai_on:
        facts = {
            "metrics": metrics,
            "category_counts": category_counts.to_dict(),
            "issue_counts": all_issue_counts.to_dict(),
        }
        allowed = {int(n) for n in re.findall(r"\d+", json.dumps(facts))}
        prompt = (
            "Write a concise summary (2-4 sentences) of this dataset's cleaning results for a "
            "non-technical reader, plus up to 4 short recommendations. Use ONLY the numbers in the "
            "facts below and do not compute new ones. State that records are not externally verified.\n"
            'Reply as JSON: {"summary": "...", "recommendations": ["..."]}\n'
            f"Facts: {json.dumps(facts)}"
        )
        try:
            summary, recs = validate_summary(parse_json_response(caller(SYSTEM_PROMPT, prompt)), allowed)
        except Exception as exc:  # noqa: BLE001
            fallbacks += 1
            logger.warning("AI summary failed validation: %s", exc)
            result.warnings.append(f"AI summary rejected ({exc}); template summary used.")
    result.summary, result.recommendations = summary, recs

    # 4) Issue explanations
    explanations = {k: ISSUE_EXPLANATIONS[k] for k in all_issue_counts.index if k in ISSUE_EXPLANATIONS}
    sources = {k: "template" for k in explanations}
    if ai_on and explanations:
        prompt = (
            "For each issue type below, write ONE plain-English sentence (max 40 words) explaining "
            "what it means and what a person should do. Do not claim anything is verified or wrong "
            "beyond what the issue type says.\n"
            'Reply as JSON: {"explanations": {"<issue_type>": "<sentence>"}}\n'
            f"Issue types and counts: {json.dumps(all_issue_counts.to_dict())}"
        )
        try:
            valid = validate_explanations(parse_json_response(caller(SYSTEM_PROMPT, prompt)),
                                          set(explanations))
            for key, text in valid.items():
                explanations[key] = text
                sources[key] = "ai (validated)"
            if len(valid) < len(explanations):
                fallbacks += 1
        except Exception as exc:  # noqa: BLE001
            fallbacks += 1
            logger.warning("AI explanations failed validation: %s", exc)
            result.warnings.append(f"AI explanations rejected ({exc}); template text used.")

    result.explanations = pd.DataFrame({
        "issue_type": list(explanations),
        "count": [int(all_issue_counts[k]) for k in explanations],
        "explanation": list(explanations.values()),
        "source": [sources[k] for k in explanations],
    })

    result.mode = "rule-based" if not ai_on else ("ai (with fallbacks)" if fallbacks else "ai")
    logger.info("AI analysis mode: %s", result.mode)
    return result
