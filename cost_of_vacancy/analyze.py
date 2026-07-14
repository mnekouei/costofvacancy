"""Orchestrates a full hospital + specialty lookup into a VacancyCostResult."""
from .benchmarks import VacancyBenchmarks
from .facility_affiliations import best_hospital_match, find_npis_for_ccn, filter_npis_by_specialty
from .provider_utilization import fetch_provider_financials
from .vacancy_cost import compute_cost_of_vacancy

DEFAULT_MAX_PROVIDERS = 25


def run_analysis(
    client,
    hospital,
    specialty,
    vacant_days=365,
    benchmarks=None,
    state=None,
    max_providers=DEFAULT_MAX_PROVIDERS,
    hospital_dataset_id=None,
    facility_dataset_id=None,
    specialty_dataset_id=None,
    utilization_dataset_id=None,
):
    """Raises HospitalNotFoundError / AmbiguousHospitalError (see
    exceptions.py) if `hospital` can't be resolved to a unique CMS record.
    """
    benchmarks = benchmarks or VacancyBenchmarks()

    hospital_row = best_hospital_match(client, hospital, state=state, dataset_id=hospital_dataset_id)
    ccn = hospital_row.get("facility_id")
    canonical_hospital_name = hospital_row.get("facility_name", hospital)

    npis = find_npis_for_ccn(client, ccn, dataset_id=facility_dataset_id)
    npis = filter_npis_by_specialty(client, npis, specialty, dataset_id=specialty_dataset_id)
    npis = npis[:max_providers]

    financials = fetch_provider_financials(client, npis, dataset_id=utilization_dataset_id)

    return compute_cost_of_vacancy(
        hospital=canonical_hospital_name,
        specialty=specialty,
        provider_financials=financials,
        benchmarks=benchmarks,
        vacant_days=vacant_days,
        queried_hospital=hospital,
        hospital_ccn=ccn,
    )
