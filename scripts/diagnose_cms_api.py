"""One-off diagnostic: run this in an environment with real internet access
(e.g. Google Colab) to discover the current, correct CMS dataset ids and
API URL shape. Paste the printed output back so cms_client.py /
facility_affiliations.py / provider_utilization.py can be fixed to match
reality instead of guessed defaults.
"""
import json

import requests

TITLES_OF_INTEREST = [
    "facility affiliation",
    "national downloadable file",
    "medicare physician & other practitioners - by provider",
]


def dump(label, obj, limit=1500):
    text = json.dumps(obj, indent=2)[:limit]
    print(f"\n--- {label} ---\n{text}\n")


def main():
    print("=== 1. Site-wide DCAT catalog: data.cms.gov/data.json ===")
    try:
        catalog = requests.get("https://data.cms.gov/data.json", timeout=30).json()
        datasets = catalog.get("dataset", [])
        print(f"catalog has {len(datasets)} datasets")
        for entry in datasets:
            title = (entry.get("title") or "").lower()
            if any(t in title for t in TITLES_OF_INTEREST):
                dump(f"data.json match: {entry.get('title')}", entry)
    except Exception as exc:
        print(f"FAILED: {exc}")

    print("\n=== 2. Provider Data Catalog metastore ===")
    for keyword in ("Facility Affiliation", "National Downloadable File"):
        url = f"https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items?keyword={keyword.replace(' ', '%20')}"
        try:
            resp = requests.get(url, timeout=30)
            print(f"\nGET {url} -> {resp.status_code}")
            if resp.ok:
                items = resp.json()
                for item in items[:3]:
                    dump(f"metastore match for '{keyword}'", item)
        except Exception as exc:
            print(f"FAILED for {keyword!r}: {exc}")

    print("\n=== 3. Try data-api/v1/dataset/{id}/data against a known-good id ===")
    # Hospital General Information is widely cited as xubh-q36u -- use it as a
    # control to confirm this URL *pattern* works at all, independent of the
    # ids we're trying to discover for facility affiliation / specialty data.
    for candidate_id in ["xubh-q36u"]:
        url = f"https://data.cms.gov/data-api/v1/dataset/{candidate_id}/data?size=1"
        try:
            resp = requests.get(url, timeout=30)
            print(f"GET {url} -> {resp.status_code}")
            if resp.ok:
                dump(f"sample row for {candidate_id}", resp.json())
        except Exception as exc:
            print(f"FAILED: {exc}")


if __name__ == "__main__":
    main()
