"""Resolve a hospital name + specialty into the set of clinician NPIs CMS
reports as affiliated with that facility.

Two CMS Provider Data Catalog datasets are combined:

* **Facility Affiliation** (default id ``27ea-46a8``) -- links each
  clinician NPI to the facilities (hospitals) they're affiliated with.
* **National Downloadable File** (default id ``mj5m-pzi6``) -- gives each
  NPI's primary specialty, used to narrow the affiliated clinicians down
  to the requested specialty.

Both ids are CMS Provider Data Catalog short ids that have been stable for
years, but datasets do get retired/replaced, so callers can override them
explicitly (see ``cli.py --facility-dataset-id`` / ``--specialty-dataset-id``).
"""
from .text_match import find_column, name_matches

FACILITY_AFFILIATION_TITLE_HINTS = ["facility affiliation"]
NATIONAL_DOWNLOADABLE_TITLE_HINTS = ["national downloadable file"]

DEFAULT_FACILITY_AFFILIATION_ID = "27ea-46a8"
DEFAULT_NATIONAL_DOWNLOADABLE_ID = "mj5m-pzi6"


def _resolve(client, hints, default_id):
    try:
        return client.resolve_dataset_id(hints)
    except Exception:
        return default_id


def find_npis_for_hospital(client, hospital_name, dataset_id=None, fetch_limit=5000):
    """Return NPIs of clinicians CMS lists as affiliated with `hospital_name`."""
    fa_id = dataset_id or _resolve(client, FACILITY_AFFILIATION_TITLE_HINTS, DEFAULT_FACILITY_AFFILIATION_ID)
    rows = client.fetch_rows(fa_id, keyword=hospital_name, limit=fetch_limit)
    if not rows:
        return []

    columns = list(rows[0].keys())
    npi_col = find_column(columns, "npi", "rndrng_npi")
    facility_col = find_column(columns, "facility_name", "facility name", "facility")
    type_col = find_column(columns, "facility_type", "facility type")

    matched = set()
    for row in rows:
        facility_value = row.get(facility_col, "") if facility_col else ""
        if not name_matches(hospital_name, facility_value):
            continue
        if type_col and row.get(type_col) and "hospital" not in str(row[type_col]).lower():
            continue
        npi = row.get(npi_col) if npi_col else None
        if npi:
            matched.add(str(npi))
    return sorted(matched)


def filter_npis_by_specialty(client, npis, specialty, dataset_id=None, fetch_limit=20000):
    """Narrow a list of NPIs down to those whose CMS-reported primary
    specialty matches `specialty` (substring, case-insensitive).
    """
    if not npis or not specialty:
        return list(npis)

    ndf_id = dataset_id or _resolve(client, NATIONAL_DOWNLOADABLE_TITLE_HINTS, DEFAULT_NATIONAL_DOWNLOADABLE_ID)
    rows = client.fetch_rows(ndf_id, keyword=specialty, limit=fetch_limit)
    if not rows:
        return []

    columns = list(rows[0].keys())
    npi_col = find_column(columns, "npi")
    spec_col = find_column(columns, "pri_spec", "primary specialty", "specialty", "provider_type")

    specialty_npis = set()
    for row in rows:
        spec_value = str(row.get(spec_col, "")) if spec_col else ""
        if specialty.lower() in spec_value.lower():
            npi = row.get(npi_col) if npi_col else None
            if npi:
                specialty_npis.add(str(npi))

    npi_set = {str(n) for n in npis}
    return sorted(npi_set & specialty_npis)
