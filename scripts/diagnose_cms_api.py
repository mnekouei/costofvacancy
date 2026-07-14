"""Round 3: confirm (a) the Hospital General Information dataset id/fields
so a hospital name can be resolved to its CMS Certification Number (CCN),
(b) that DKAN's conditions[] server-side filtering works against
provider-data/api/1/datastore/query (needed -- Facility Affiliation and
National Downloadable File have 2-3M rows each, too many to page through
client-side), and (c) the exact filter[] param shape + field casing on the
data-api/v1 physician-billing endpoint confirmed working in round 1.
"""
import json

import requests

TIMEOUT = 20
HGI_CANDIDATE_ID = "xubh-q36u"  # per third-party docs; unverified until now
FACILITY_AFFILIATION_ID = "27ea-46a8"
NDF_ID = "mj5m-pzi6"
UTILIZATION_LONG_UUID = "8889d81e-2ee7-448f-8713-f071038289b5"  # confirmed working in round 1


def try_get(label, url, params=None):
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        print(f"\n[{resp.status_code}] {label}\n  {resp.url}")
        if resp.ok:
            try:
                body = resp.json()
                print(json.dumps(body, indent=2)[:2000])
                return body
            except ValueError:
                print(f"  (non-JSON body, {len(resp.content)} bytes)")
        else:
            print(f"  body: {resp.text[:300]}")
        return None
    except requests.RequestException as exc:
        print(f"[FAIL] {label}: {exc}")
        return None


def main():
    print("=== A: Hospital General Information dataset -- basic query ===")
    try_get(
        "HGI sample row",
        f"https://data.cms.gov/provider-data/api/1/datastore/query/{HGI_CANDIDATE_ID}/0",
        params={"limit": 1},
    )

    print("\n=== B: HGI filtered by facility name (conditions[] LIKE) ===")
    try_get(
        "HGI LIKE filter on facility name",
        f"https://data.cms.gov/provider-data/api/1/datastore/query/{HGI_CANDIDATE_ID}/0",
        params={
            "conditions[0][property]": "facility_name",
            "conditions[0][value]": "%MAYO CLINIC HOSPITAL%",
            "conditions[0][operator]": "like",
            "limit": 5,
        },
    )

    print("\n=== C: Facility Affiliation filtered by CCN (conditions[] exact) ===")
    print("(using CCN 090012 seen in round-2 sample output as a guaranteed-real value)")
    try_get(
        "Facility Affiliation filtered by CCN",
        f"https://data.cms.gov/provider-data/api/1/datastore/query/{FACILITY_AFFILIATION_ID}/0",
        params={
            "conditions[0][property]": "facility_affiliations_certification_number",
            "conditions[0][value]": "090012",
            "conditions[0][operator]": "=",
            "limit": 5,
        },
    )

    print("\n=== D: National Downloadable File filtered by specialty (conditions[] LIKE) ===")
    try_get(
        "NDF LIKE filter on pri_spec",
        f"https://data.cms.gov/provider-data/api/1/datastore/query/{NDF_ID}/0",
        params={
            "conditions[0][property]": "pri_spec",
            "conditions[0][value]": "%CARDIOLOGY%",
            "conditions[0][operator]": "like",
            "limit": 5,
        },
    )

    print("\n=== E: data-api/v1 filter[] param shape + field casing (known-good NPI) ===")
    try_get(
        "Utilization filter by NPI, capitalized column",
        f"https://data.cms.gov/data-api/v1/dataset/{UTILIZATION_LONG_UUID}/data",
        params={"filter[Rndrng_NPI]": "1003000126", "size": 5},
    )
    try_get(
        "Utilization filter by NPI, lowercase column",
        f"https://data.cms.gov/data-api/v1/dataset/{UTILIZATION_LONG_UUID}/data",
        params={"filter[rndrng_npi]": "1003000126", "size": 5},
    )


if __name__ == "__main__":
    main()
