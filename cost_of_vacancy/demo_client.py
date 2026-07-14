"""Offline stand-in for CMSClient, backed by small bundled fixture files.

Used by `--demo` on the CLI and by the test suite so the full lookup ->
match -> compute pipeline can be exercised without network access. It
implements the same interface as `cms_client.CMSClient`
(`resolve_dataset_id`, `fetch_rows`, `columns_for`, `datastore_query`), so
`analyze.run_analysis` works unmodified against either one.
"""
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Provider Data Catalog datasets, queried by their real dataset id (matches
# the hardcoded ids in facility_affiliations.py -- those aren't resolved
# dynamically since, unlike the utilization dataset, their ids don't rotate
# on CMS's annual release cadence).
_DATASTORE_FILES = {
    "xubh-q36u": "hospital_general_information_sample.json",       # Hospital General Information
    "27ea-46a8": "facility_affiliation_sample.json",                # Facility Affiliation
    "mj5m-pzi6": "national_downloadable_file_sample.json",          # National Downloadable File
}

# The utilization dataset's id rotates yearly in real life, so real code
# resolves it dynamically by title via resolve_dataset_id(); mirror that
# indirection here with a stable logical key.
_FETCH_ROWS_FILES = {
    "utilization": "utilization_sample.json",
}

_TITLE_HINTS_TO_DATASET = {
    ("medicare physician", "other practitioners", "by provider"): "utilization",
}


def _matches_condition(row, prop, operator, value):
    row_value = row.get(prop)
    if operator == "=":
        return str(row_value) == str(value)
    if operator == "like":
        needle = str(value).strip("%").upper()
        return needle in str(row_value or "").upper()
    if operator == "in":
        values = value if isinstance(value, (list, tuple)) else [value]
        return str(row_value) in {str(v) for v in values}
    raise ValueError(f"Unsupported demo condition operator: {operator!r}")


class DemoCMSClient:
    def __init__(self):
        self._cache = {}

    def _load(self, filename):
        if filename not in self._cache:
            with open(FIXTURES_DIR / filename) as f:
                self._cache[filename] = json.load(f)
        return self._cache[filename]

    def resolve_dataset_id(self, title_must_include, title_must_exclude=()):
        key = tuple(s.lower() for s in title_must_include)
        for hints, dataset_id in _TITLE_HINTS_TO_DATASET.items():
            if all(any(h in k for k in key) for h in hints):
                return dataset_id
        raise KeyError(f"No demo dataset matches title hints {title_must_include!r}")

    def fetch_rows(self, dataset_id, keyword=None, column_filters=None, limit=None):
        filename = _FETCH_ROWS_FILES.get(dataset_id)
        if not filename:
            raise KeyError(f"Unknown demo fetch_rows dataset id: {dataset_id!r}")
        result = self._load(filename)
        if keyword:
            kw = keyword.lower()
            result = [r for r in result if any(kw in str(v).lower() for v in r.values())]
        if column_filters:
            for col, val in column_filters.items():
                result = [r for r in result if str(r.get(col)) == str(val)]
        if limit:
            result = result[:limit]
        return result

    def columns_for(self, dataset_id):
        filename = _FETCH_ROWS_FILES.get(dataset_id)
        if not filename:
            raise KeyError(f"Unknown demo fetch_rows dataset id: {dataset_id!r}")
        rows = self._load(filename)
        return list(rows[0].keys()) if rows else []

    def datastore_query(self, dataset_id, conditions=None, limit=100, offset=0):
        filename = _DATASTORE_FILES.get(dataset_id)
        if not filename:
            raise KeyError(f"Unknown demo datastore dataset id: {dataset_id!r}")
        rows = self._load(filename)
        if conditions:
            for prop, operator, value in conditions:
                rows = [r for r in rows if _matches_condition(r, prop, operator, value)]
        return rows[offset:offset + limit]
