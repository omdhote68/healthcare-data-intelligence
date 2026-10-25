"""Cleaning functions: text, phone numbers and URLs.

Golden rules:
  * Never invent data. Missing stays missing. We never add digits to a phone number.
  * Keep the original value so every change can be audited (see the change log).
  * "Looks valid" is NOT "is correct". We only check the FORMAT.

Phone formatting assumes Indian-style numbers for grouping (e.g. +91 98765 55501),
but other numbers are kept as plain digits rather than guessed at.
"""

import re
from urllib.parse import urlparse

import pandas as pd

from src.config import PHONE_MAX_DIGITS, PHONE_MIN_DIGITS, TEXT_COLUMNS
from src.logger import get_logger

logger = get_logger()

PLACEHOLDERS = {"nan", "none", "null", "n/a", "na", "-", "--", "nil", "unknown"}
SMALL_WORDS = {"and", "of", "the", "for", "in", "at", "a", "an", "&"}
_HOST_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$", re.IGNORECASE
)


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------
def clean_text(value):
    """Trim, collapse whitespace, turn placeholders like 'N/A' into None."""
    if value is None or pd.isna(value):
        return None
    text = str(value).replace("\u00a0", " ")
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)        # control characters
    text = re.sub(r"\s+", " ", text).strip()
    if not text or text.lower() in PLACEHOLDERS:
        return None
    return text


def smart_title(text):
    """Tidy capitalisation without breaking names like "Children's" or "McDonald".

    Only all-lowercase words are capitalised. If the whole text is SHOUTING,
    longer words are capitalised too. Mixed-case words and short acronyms are kept.
    """
    if text is None:
        return None
    shouting = text.isupper()
    words = []
    for index, word in enumerate(text.split(" ")):
        letters = [c for c in word if c.isalpha()]
        if not letters:
            words.append(word)
        elif word.islower():
            words.append(word if (index > 0 and word in SMALL_WORDS) else word.capitalize())
        elif word.isupper() and shouting and len(letters) > 3:
            words.append(word.capitalize())
        else:
            words.append(word)
    return " ".join(words)


def match_key(text) -> str:
    """Lowercase letters/digits only, single spaces. Used to compare records."""
    if text is None or (not isinstance(text, str) and pd.isna(text)):
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(text).lower())).strip()


# --------------------------------------------------------------------------
# Phone numbers
# --------------------------------------------------------------------------
def clean_phone(value):
    """Return (cleaned_text, match_key, status). Status: ok / missing / invalid.

    * Only formatting changes - no digits are ever added or guessed.
    * 'invalid' means the number looks wrong (letters, too short/long, all one digit).
      We keep the text so a human can look at it.
    * 'ok' means only that the FORMAT is plausible, not that the number works.
    """
    text = clean_text(value)
    if text is None:
        return None, "", "missing"

    if re.search(r"[A-Za-z]", text):
        return text, "", "invalid"

    digits = re.sub(r"\D", "", text)
    if not (PHONE_MIN_DIGITS <= len(digits) <= PHONE_MAX_DIGITS) or len(set(digits)) == 1:
        return text, "", "invalid"

    has_plus = text.startswith("+")
    if has_plus and len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        formatted = f"+91 {digits[2:7]} {digits[7:]}"
    elif has_plus:
        formatted = "+" + digits
    elif len(digits) == 10 and digits[0] in "6789":
        formatted = f"{digits[:5]} {digits[5:]}"
    else:
        formatted = digits

    key = digits[-10:] if len(digits) >= 10 else digits
    return formatted, key, "ok"


# --------------------------------------------------------------------------
# URLs
# --------------------------------------------------------------------------
def clean_url(value):
    """Return (cleaned_url, status, scheme_added). Status: ok / missing / invalid.

    A missing 'https://' is added (and recorded as a change). 'ok' means the URL is
    well-formed - it does NOT mean the website exists or belongs to the practice.
    """
    text = clean_text(value)
    if text is None:
        return None, "missing", False
    if " " in text:
        return text, "invalid", False

    candidate, scheme_added = text, False
    if "://" not in candidate:
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", candidate):
            return text, "invalid", False       # e.g. "htp:/bright-smile"
        candidate = "https://" + candidate
        scheme_added = True

    try:
        parsed = urlparse(candidate)
        host = parsed.hostname or ""
    except ValueError:
        return text, "invalid", False

    if parsed.scheme.lower() not in ("http", "https") or not _HOST_RE.match(host):
        return text, "invalid", False
    return candidate, "ok", scheme_added


# --------------------------------------------------------------------------
# Whole table
# --------------------------------------------------------------------------
def clean_dataframe(df: pd.DataFrame):
    """Clean a standardised table. Returns (cleaned_df, changes_df).

    cleaned_df keeps `phone_original` and `website_original`, adds status columns,
    and internal matching columns that start with "_" (dropped on export).
    changes_df lists every value that was changed: source_row, field, original, cleaned.
    """
    out = pd.DataFrame({"source_row": df["source_row"].values})
    changes = []

    def log_change(row_id, field_name, original, cleaned):
        original_text = None if (original is None or pd.isna(original)) else str(original)
        if original_text != cleaned:
            changes.append({
                "source_row": row_id, "field": field_name,
                "original": original_text, "cleaned": cleaned,
            })

    # Plain text columns
    for column in TEXT_COLUMNS:
        cleaned_values = [smart_title(clean_text(v)) for v in df[column]]
        for row_id, original, cleaned in zip(out["source_row"], df[column], cleaned_values):
            log_change(row_id, column, original, cleaned)
        out[column] = cleaned_values

    # Phone
    phone_results = [clean_phone(v) for v in df["phone"]]
    out["phone"] = [r[0] for r in phone_results]
    out["phone_status"] = [r[2] for r in phone_results]
    for row_id, original, result in zip(out["source_row"], df["phone"], phone_results):
        log_change(row_id, "phone", original, result[0])

    # Website and source URL
    for column in ("website", "source_url"):
        results = [clean_url(v) for v in df[column]]
        out[column] = [r[0] for r in results]
        out[f"{column}_status"] = [r[1] for r in results]
        for row_id, original, result in zip(out["source_row"], df[column], results):
            log_change(row_id, column, original, result[0])

    # Originals kept side by side for the two most heavily edited fields
    out["phone_original"] = list(df["phone"])
    out["website_original"] = list(df["website"])

    # Internal matching columns (used for duplicate detection)
    out["_name_key"] = [match_key(v) for v in out["practice_name"]]
    out["_city_key"] = [match_key(v) for v in out["city"]]
    out["_phone_key"] = [r[1] for r in phone_results]

    changes_df = pd.DataFrame(changes, columns=["source_row", "field", "original", "cleaned"])
    logger.info("Cleaning finished: %d values changed across %d rows", len(changes_df), len(out))
    return out, changes_df
