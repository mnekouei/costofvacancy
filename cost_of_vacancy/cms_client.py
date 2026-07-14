"""Thin client for the public data.cms.gov API.

CMS re-publishes its provider datasets on a yearly cadence and the dataset
UUIDs in the URL change between releases, so this client resolves dataset
ids dynamically from the site-wide DCAT catalog (``data.cms.gov/data.json``)
by matching on title, instead of hardcoding UUIDs that would silently go
stale. Two provider-data-catalog datasets whose short ids have stayed
stable for years are used as fallback defaults; everything else is
resolved live or can be overridden explicitly.

No CMS API key is required -- these are open data endpoints.
"""
import re

import requests

CATALOG_URL = "https://data.cms.gov/data.json"
DATA_API_TEMPLATE = "https://data.cms.gov/data-api/v1/dataset/{dataset_id}/data"
PROVIDER_DATA_QUERY_TEMPLATE = "https://data.cms.gov/provider-data/api/1/datastore/query/{dataset_id}/0"
PAGE_SIZE = 500


class CMSApiError(RuntimeError):
    """Raised when the CMS API can't be reached or a dataset can't be resolved."""


class CMSClient:
    """Minimal paging JSON client for data.cms.gov's data-api/v1 endpoints."""

    def __init__(self, session=None, timeout=30, max_pages=40, user_agent=None):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_pages = max_pages
        self.session.headers.setdefault(
            "User-Agent", user_agent or "cost-of-vacancy-cli/1.0 (+https://data.cms.gov)"
        )
        self._catalog_cache = None

    def _get_json(self, url, params=None):
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise CMSApiError(f"Request to {url} failed: {exc}") from exc
        try:
            return resp.json()
        except ValueError as exc:
            raise CMSApiError(f"Non-JSON response from {url}: {resp.text[:200]!r}") from exc

    def resolve_dataset_id(self, title_must_include, title_must_exclude=()):
        """Find a dataset id in the CMS catalog whose title contains every
        string in `title_must_include` (case-insensitive) and none of
        `title_must_exclude`.
        """
        if self._catalog_cache is None:
            self._catalog_cache = self._get_json(CATALOG_URL)
        datasets = self._catalog_cache.get("dataset", []) if isinstance(self._catalog_cache, dict) else []
        must_include = [s.lower() for s in title_must_include]
        must_exclude = [s.lower() for s in title_must_exclude]
        for entry in datasets:
            title = (entry.get("title") or "").lower()
            if all(s in title for s in must_include) and not any(s in title for s in must_exclude):
                dataset_id = self._extract_dataset_id(entry)
                if dataset_id:
                    return dataset_id
        raise CMSApiError(
            f"Could not resolve a CMS dataset id for a title containing {title_must_include!r} "
            f"(excluding {title_must_exclude!r}). Pass an explicit dataset id instead."
        )

    @staticmethod
    def _extract_dataset_id(entry):
        for dist in entry.get("distribution", []) or []:
            for key in ("accessURL", "downloadURL"):
                url = dist.get(key, "") or ""
                m = re.search(r"data-api/v1/dataset/([0-9a-zA-Z-]+)/data", url)
                if m:
                    return m.group(1)
        identifier = entry.get("identifier", "") or ""
        m = re.search(r"([0-9a-fA-F]{4}-[0-9a-fA-F]{4})$", identifier)
        if m:
            return m.group(1)
        return None

    def fetch_rows(self, dataset_id, keyword=None, column_filters=None, limit=None):
        """Page through a dataset, optionally narrowed by a full-text
        `keyword` and/or exact-match `column_filters`. Stops after
        `max_pages` pages as a safety cap on very large datasets.
        """
        url = DATA_API_TEMPLATE.format(dataset_id=dataset_id)
        rows = []
        offset = 0
        for _ in range(self.max_pages):
            params = {"size": PAGE_SIZE, "offset": offset}
            if keyword:
                params["keyword"] = keyword
            if column_filters:
                for col, val in column_filters.items():
                    params[f"filter[{col}]"] = val
            page = self._get_json(url, params=params)
            if isinstance(page, dict):
                page = page.get("data") or page.get("results") or []
            if not page:
                break
            rows.extend(page)
            if limit and len(rows) >= limit:
                return rows[:limit]
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return rows

    def columns_for(self, dataset_id):
        rows = self.fetch_rows(dataset_id, limit=1)
        return list(rows[0].keys()) if rows else []

    @staticmethod
    def _condition_params(conditions):
        """Build DKAN ``conditions[N][property/operator/value]`` query params.

        `conditions` is a list of (property, operator, value) tuples.
        Multiple conditions are ANDed together by the datastore query API.
        For operator "in", `value` should be a list -- `requests` encodes a
        list-valued param as repeated `key=v1&key=v2`, which is exactly the
        `conditions[N][value][]=v1&conditions[N][value][]=v2` shape DKAN expects.
        """
        params = {}
        for i, (prop, operator, value) in enumerate(conditions):
            params[f"conditions[{i}][property]"] = prop
            params[f"conditions[{i}][operator]"] = operator
            key = f"conditions[{i}][value][]" if operator == "in" else f"conditions[{i}][value]"
            params[key] = value
        return params

    def datastore_query(self, dataset_id, conditions=None, limit=100, offset=0):
        """Query a Provider Data Catalog dataset (e.g. Facility Affiliation,
        Hospital General Information, National Downloadable File) via CMS's
        DKAN datastore API, which supports server-side filtering -- required
        since these datasets run into the millions of rows and can't be
        paged through client-side.
        """
        url = PROVIDER_DATA_QUERY_TEMPLATE.format(dataset_id=dataset_id)
        params = {"limit": limit, "offset": offset}
        if conditions:
            params.update(self._condition_params(conditions))
        data = self._get_json(url, params=params)
        return data.get("results", []) if isinstance(data, dict) else []
