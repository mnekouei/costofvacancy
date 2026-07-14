"""Resolve a hospital name + specialty into the set of clinician NPIs CMS
reports as affiliated with that facility.

Confirmed against the live CMS Provider Data Catalog API (see
scripts/diagnose_cms_api.py) rather than guessed:

* **Hospital General Information** (``xubh-q36u``) maps a hospital name to
  its CMS Certification Number (CCN, called ``facility_id`` here).
* **Facility Affiliation** (``27ea-46a8``) maps a CCN to the NPIs of
  clinicians affiliated with that facility -- it has no hospital-name field
  at all, only the CCN, which is why the Hospital General Information
  lookup has to happen first.
* **National Downloadable File** (``mj5m-pzi6``) gives each NPI's primary
  specialty (``pri_spec``), used to narrow the affiliated clinicians down
  to the requested specialty.

All three are queried through CMS's DKAN datastore API
(``provider-data/api/1/datastore/query/{id}/0``), which supports real
server-side filtering -- required since Facility Affiliation and the
National Downloadable File each have millions of rows.
"""
from .exceptions import AmbiguousHospitalError, HospitalNotFoundError
from .text_match import token_overlap_score

HOSPITAL_GENERAL_INFO_ID = "xubh-q36u"
FACILITY_AFFILIATION_ID = "27ea-46a8"
NATIONAL_DOWNLOADABLE_FILE_ID = "mj5m-pzi6"

MIN_MATCH_SCORE = 0.6
AMBIGUOUS_SCORE_GAP = 0.15


def _chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def resolve_hospital(client, hospital_name, state=None, dataset_id=None, limit=25):
    """Look up candidate Hospital General Information rows for `hospital_name`,
    scored by token overlap, best match first. Returns a list of
    (score, row) tuples; `row` has at least `facility_id`, `facility_name`, `state`.
    """
    ds_id = dataset_id or HOSPITAL_GENERAL_INFO_ID
    conditions = [("facility_name", "like", f"%{hospital_name.upper()}%")]
    if state:
        conditions.append(("state", "=", state.upper()))
    rows = client.datastore_query(ds_id, conditions=conditions, limit=limit)

    scored = [(token_overlap_score(hospital_name, row.get("facility_name", "")), row) for row in rows]
    scored.sort(key=lambda pair: -pair[0])
    return scored


def best_hospital_match(client, hospital_name, state=None, dataset_id=None):
    """Resolve `hospital_name` to a single best-matching Hospital General
    Information row, or raise HospitalNotFoundError / AmbiguousHospitalError.
    """
    scored = resolve_hospital(client, hospital_name, state=state, dataset_id=dataset_id)
    if not scored:
        raise HospitalNotFoundError(
            f"No hospital matching '{hospital_name}' found in CMS Hospital General Information data."
        )

    best_score, best_row = scored[0]
    if best_score < MIN_MATCH_SCORE:
        candidates = [(score, row.get("facility_name", ""), row.get("state", "")) for score, row in scored[:5]]
        raise AmbiguousHospitalError(hospital_name, candidates)

    if len(scored) > 1:
        second_score, _ = scored[1]
        if best_score - second_score < AMBIGUOUS_SCORE_GAP:
            candidates = [(score, row.get("facility_name", ""), row.get("state", "")) for score, row in scored[:5]]
            raise AmbiguousHospitalError(hospital_name, candidates)

    return best_row


def find_npis_for_ccn(client, ccn, dataset_id=None, limit=1000):
    """Return NPIs of clinicians CMS lists as affiliated with the hospital
    identified by `ccn` (a CMS Certification Number).
    """
    ds_id = dataset_id or FACILITY_AFFILIATION_ID
    conditions = [("facility_affiliations_certification_number", "=", ccn)]
    rows = client.datastore_query(ds_id, conditions=conditions, limit=limit)
    return sorted({row["npi"] for row in rows if row.get("npi")})


def filter_npis_by_specialty(client, npis, specialty, dataset_id=None, chunk_size=40):
    """Narrow a list of NPIs down to those whose CMS-reported primary
    specialty matches `specialty` (substring, case-insensitive).
    """
    if not npis or not specialty:
        return list(npis)

    ds_id = dataset_id or NATIONAL_DOWNLOADABLE_FILE_ID
    specialty_upper = specialty.upper()
    matched = set()

    for chunk in _chunked(list(npis), chunk_size):
        conditions = [
            ("npi", "in", chunk),
            ("pri_spec", "like", f"%{specialty_upper}%"),
        ]
        rows = client.datastore_query(ds_id, conditions=conditions, limit=chunk_size * 10)
        chunk_set = set(chunk)
        for row in rows:
            npi = row.get("npi")
            # Defensive client-side re-check in case the API doesn't AND the
            # two conditions the way we expect -- cheap given chunk_size is small.
            if npi in chunk_set and specialty_upper in str(row.get("pri_spec", "")).upper():
                matched.add(npi)

    return sorted(matched)
