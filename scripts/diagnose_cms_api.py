"""Round 2: the provider-summary datasets (Medicare Physician & Other
Practitioners) resolve fine via data.json with a long-UUID accessURL. The
Provider Data Catalog datasets (Facility Affiliation, National Downloadable
File) do NOT appear in data.json at all, and the short dataset id shown in
their page URL (e.g. 27ea-46a8) 404s against data-api/v1/dataset/{id}/data.
This script tries several plausible API shapes for those Provider Data
Catalog sets directly, with short per-request timeouts so a dead endpoint
doesn't hang the whole run.
"""
import json

import requests

SHORT_IDS = {
    "Facility Affiliation": "27ea-46a8",
    "National Downloadable File": "mj5m-pzi6",
}

TIMEOUT = 12


def try_get(label, url, params=None):
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        print(f"[{resp.status_code}] {label}: {resp.url}")
        if resp.ok:
            try:
                body = resp.json()
                text = json.dumps(body, indent=2)
                print(text[:1500])
            except ValueError:
                print(f"  (non-JSON body, {len(resp.content)} bytes)")
        return resp if resp.ok else None
    except requests.RequestException as exc:
        print(f"[FAIL] {label}: {exc}")
        return None


def main():
    for name, short_id in SHORT_IDS.items():
        print(f"\n=== {name} ({short_id}) ===")

        # A: direct metastore item lookup (should be O(1), not a search)
        try_get(
            "metastore item detail",
            f"https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/{short_id}",
        )

        # B: DKAN-style datastore query using the dataset id directly
        try_get(
            "datastore query by dataset id",
            f"https://data.cms.gov/provider-data/api/1/datastore/query/{short_id}/0",
            params={"limit": 1},
        )

        # C: same but as a top-level resource_id query param
        try_get(
            "datastore query via resource_id param",
            "https://data.cms.gov/provider-data/api/1/datastore/query",
            params={"resource_id": short_id, "limit": 1},
        )

    print("\n=== D: does data.cms.gov publish a separate provider-data catalog json? ===")
    for url in [
        "https://data.cms.gov/provider-data/data.json",
        "https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items",
    ]:
        try_get("catalog probe", url)


if __name__ == "__main__":
    main()
