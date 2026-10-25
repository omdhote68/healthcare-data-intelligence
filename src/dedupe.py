"""Duplicate detection.

Two levels, deliberately different:
  * EXACT duplicate  - same name, city and phone after cleaning. The later copy is
                       removed (the first is kept) and listed so nothing silently vanishes.
  * POTENTIAL duplicate - same valid phone number, or very similar names in the same
                       city. These are FLAGGED ONLY, never removed: a human must decide,
                       because branches of one group can share names or phone numbers.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import combinations

import pandas as pd

from src.config import FUZZY_THRESHOLD, MAX_FUZZY_GROUP
from src.logger import get_logger

logger = get_logger()


@dataclass
class DedupeResult:
    kept: pd.DataFrame
    removed: pd.DataFrame          # exact duplicates, with `duplicate_of_row`
    potential_pairs: pd.DataFrame  # pairs flagged for human review


def find_duplicates(df: pd.DataFrame, fuzzy_threshold: float = FUZZY_THRESHOLD) -> DedupeResult:
    """Split cleaned records into kept / removed and find potential duplicate pairs."""
    seen = {}
    removed_rows = []
    kept_index = []

    for idx, row in df.iterrows():
        key = (row["_name_key"], row["_city_key"], row["_phone_key"])
        eligible = bool(row["_name_key"]) and bool(row["_city_key"] or row["_phone_key"])
        if eligible and key in seen:
            record = row.to_dict()
            record["duplicate_of_row"] = seen[key]
            removed_rows.append(record)
        else:
            if eligible:
                seen[key] = row["source_row"]
            kept_index.append(idx)

    kept = df.loc[kept_index].reset_index(drop=True)
    removed = pd.DataFrame(removed_rows, columns=list(df.columns) + ["duplicate_of_row"])

    pairs = _find_potential_pairs(kept, fuzzy_threshold)
    logger.info(
        "Duplicates: %d exact removed, %d potential pairs flagged", len(removed), len(pairs)
    )
    return DedupeResult(kept=kept, removed=removed, potential_pairs=pairs)


def _find_potential_pairs(kept: pd.DataFrame, threshold: float) -> pd.DataFrame:
    found = {}  # (row_a, row_b) -> {"reasons": set, "similarity": float}

    def register(i, j, reason):
        a, b = kept.loc[i], kept.loc[j]
        pair = tuple(sorted((int(a["source_row"]), int(b["source_row"]))))
        sim = SequenceMatcher(None, a["_name_key"], b["_name_key"]).ratio()
        entry = found.setdefault(pair, {"reasons": set(), "similarity": sim})
        entry["reasons"].add(reason)

    # Reason 1: same valid phone number
    with_phone = kept[(kept["phone_status"] == "ok") & (kept["_phone_key"] != "")]
    for _, group in with_phone.groupby("_phone_key"):
        for i, j in combinations(group.index, 2):
            register(i, j, "same phone number")

    # Reason 2: very similar names in the same city
    with_city = kept[(kept["_city_key"] != "") & (kept["_name_key"] != "")]
    for city, group in with_city.groupby("_city_key"):
        if len(group) > MAX_FUZZY_GROUP:
            logger.warning("Skipping fuzzy matching for '%s' (%d records)", city, len(group))
            continue
        for i, j in combinations(group.index, 2):
            sim = SequenceMatcher(None, kept.at[i, "_name_key"], kept.at[j, "_name_key"]).ratio()
            if sim >= threshold:
                register(i, j, "similar name in same city")

    names = dict(zip(kept["source_row"].astype(int), kept["practice_name"]))
    rows = []
    for (row_a, row_b), info in sorted(found.items()):
        rows.append({
            "source_row_a": row_a, "practice_name_a": names.get(row_a),
            "source_row_b": row_b, "practice_name_b": names.get(row_b),
            "reason": "; ".join(sorted(info["reasons"])),
            "name_similarity": round(info["similarity"], 2),
        })
    return pd.DataFrame(rows, columns=[
        "source_row_a", "practice_name_a", "source_row_b", "practice_name_b",
        "reason", "name_similarity",
    ])
