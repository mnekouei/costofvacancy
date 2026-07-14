"""Fuzzy matching helpers for reconciling free-text hospital/specialty names
against CMS record values, and for resolving CMS column names, which vary
in casing and abbreviation across dataset releases (e.g. ``Rndrng_NPI`` vs
``npi`` vs ``NPI``).
"""
import re

_STOPWORDS = {
    "hospital", "medical", "center", "centre", "regional", "the", "of",
    "and", "health", "healthcare", "system", "inc", "llc", "campus",
    "memorial", "general",
}


def _normalize_tokens(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return [t for t in text.split() if t and t not in _STOPWORDS]


def name_matches(query, candidate, min_overlap=0.6):
    """True if most of the meaningful tokens in `query` appear in `candidate`.

    Deliberately permissive (token-overlap, not exact string equality) since
    hospital names in CMS data are inconsistently abbreviated/punctuated.
    """
    if not candidate:
        return False
    q_tokens = set(_normalize_tokens(query))
    if not q_tokens:
        return False
    c_tokens = set(_normalize_tokens(candidate))
    overlap = len(q_tokens & c_tokens) / len(q_tokens)
    return overlap >= min_overlap


def find_column(columns, *candidates):
    """Resolve a logical field name to whatever column name CMS actually used.

    Tries exact (case-insensitive) matches first, then falls back to
    substring matches, so the client tolerates schema drift instead of
    breaking outright.
    """
    lower_map = {c.lower(): c for c in columns}
    for cand in candidates:
        key = cand.lower()
        if key in lower_map:
            return lower_map[key]
        key_us = key.replace(" ", "_")
        if key_us in lower_map:
            return lower_map[key_us]
    for cand in candidates:
        cand_l = cand.lower()
        for col in columns:
            if cand_l in col.lower():
                return col
    return None
