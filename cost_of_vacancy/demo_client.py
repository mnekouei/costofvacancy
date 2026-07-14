"""Offline stand-in for CMSClient, backed by small bundled fixture files.

Used by `--demo` on the CLI and by the test suite so the full lookup ->
match -> compute pipeline can be exercised without network access. It
implements the same interface as `cms_client.CMSClient`
(`resolve_dataset_id`, `fetch_rows`, `columns_for`), so `analyze.run_analysis`
works unmodified against either one.
"""
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_DATASET_FILES = {
    "facility-affiliation": "facility_affiliation_sample.json",
    "national-downloadable-file": "national_downloadable_file_sample.json",
    "utilization": "utilization_sample.json",
}

_TITLE_HINTS_TO_DATASET = {
    ("facility affiliation",): "facility-affiliation",
    ("national downloadable file",): "national-downloadable-file",
    ("medicare physician", "other practitioners", "by provider"): "utilization",
}


class DemoCMSClient:
    def __init__(self):
        self._cache = {}

    def _load(self, dataset_id):
        if dataset_id not in self._cache:
            filename = _DATASET_FILES.get(dataset_id)
            if not filename:
                raise KeyError(f"Unknown demo dataset id: {dataset_id!r}")
            with open(FIXTURES_DIR / filename) as f:
                self._cache[dataset_id] = json.load(f)
        return self._cache[dataset_id]

    def resolve_dataset_id(self, title_must_include, title_must_exclude=()):
        key = tuple(s.lower() for s in title_must_include)
        for hints, dataset_id in _TITLE_HINTS_TO_DATASET.items():
            if all(any(h in k for k in key) for h in hints):
                return dataset_id
        raise KeyError(f"No demo dataset matches title hints {title_must_include!r}")

    def fetch_rows(self, dataset_id, keyword=None, column_filters=None, limit=None):
        rows = self._load(dataset_id)
        result = rows
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
        rows = self._load(dataset_id)
        return list(rows[0].keys()) if rows else []
