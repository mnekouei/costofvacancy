"""Pull Medicare billing figures for a set of NPIs from the CMS "Medicare
Physician & Other Practitioners - by Provider" dataset.

This dataset reports, per rendering NPI per calendar year: total Medicare
beneficiaries seen, total services, total submitted charges, total Medicare
allowed amount, and total Medicare payment amount. It is Medicare
fee-for-service billing only (no private payer, Medicare Advantage, or
facility-fee revenue), which is why `vacancy_cost.py` grosses it up by an
assumed payer-mix share rather than treating it as total revenue.

The dataset id changes with each annual CMS release, so it's resolved live
from the CMS catalog by title; pass `dataset_id` explicitly to skip that
lookup (e.g. if you've pinned a specific year's release).
"""
from .text_match import find_column

UTILIZATION_TITLE_INCLUDE = ["medicare physician", "other practitioners", "by provider"]
UTILIZATION_TITLE_EXCLUDE = ["service", "geography"]


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fetch_provider_financials(client, npis, dataset_id=None):
    """Return a list of dicts with billing figures for each NPI found.

    NPIs CMS suppresses (low volume, privacy rules) or that simply have no
    Medicare billing on record won't appear in the results -- callers should
    treat a shorter result list than `npis` as expected, not an error.
    """
    if not npis:
        return []

    ds_id = dataset_id or client.resolve_dataset_id(UTILIZATION_TITLE_INCLUDE, UTILIZATION_TITLE_EXCLUDE)

    rows = []
    npi_filter_col = None
    for npi in npis:
        filter_col = npi_filter_col or "Rndrng_NPI"
        page = client.fetch_rows(ds_id, column_filters={filter_col: npi}, limit=5)
        if not page and npi_filter_col is None:
            # First filter attempt returned nothing -- the exact-match column
            # name may differ from our guess. Discover it from the schema and
            # retry once before assuming the NPI has no data.
            columns = client.columns_for(ds_id)
            resolved = find_column(columns, "Rndrng_NPI", "npi")
            if resolved and resolved != filter_col:
                npi_filter_col = resolved
                page = client.fetch_rows(ds_id, column_filters={resolved: npi}, limit=5)
        rows.extend(page)

    if not rows:
        return []

    columns = list(rows[0].keys())
    npi_col = find_column(columns, "Rndrng_NPI", "npi")
    type_col = find_column(columns, "Rndrng_Prvdr_Type", "provider_type", "specialty")
    payment_col = find_column(columns, "Tot_Mdcr_Pymt_Amt", "medicare_payment")
    charge_col = find_column(columns, "Tot_Sbmtd_Chrg", "submitted_charges")
    allowed_col = find_column(columns, "Tot_Mdcr_Alowd_Amt", "medicare_allowed")
    benes_col = find_column(columns, "Tot_Benes", "total_beneficiaries")

    result = []
    for row in rows:
        result.append({
            "npi": str(row.get(npi_col)) if npi_col else None,
            "specialty": row.get(type_col) if type_col else None,
            "medicare_payment": _to_float(row.get(payment_col)) if payment_col else 0.0,
            "submitted_charges": _to_float(row.get(charge_col)) if charge_col else 0.0,
            "medicare_allowed": _to_float(row.get(allowed_col)) if allowed_col else 0.0,
            "total_beneficiaries": _to_float(row.get(benes_col)) if benes_col else 0.0,
        })
    return result
