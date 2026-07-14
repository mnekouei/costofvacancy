"""Orchestrates a full hospital + specialty lookup into a VacancyCostResult."""
from .benchmarks import VacancyBenchmarks
from .facility_affiliations import find_npis_for_hospital, filter_npis_by_specialty
from .provider_utilization import fetch_provider_financials
from .vacancy_cost import compute_cost_of_vacancy


def run_analysis(
    client,
    hospital,
    specialty,
    vacant_days=365,
    benchmarks=None,
    facility_dataset_id=None,
    specialty_dataset_id=None,
    utilization_dataset_id=None,
):
    benchmarks = benchmarks or VacancyBenchmarks()

    npis = find_npis_for_hospital(client, hospital, dataset_id=facility_dataset_id)
    npis = filter_npis_by_specialty(client, npis, specialty, dataset_id=specialty_dataset_id)
    financials = fetch_provider_financials(client, npis, dataset_id=utilization_dataset_id)

    return compute_cost_of_vacancy(
        hospital=hospital,
        specialty=specialty,
        provider_financials=financials,
        benchmarks=benchmarks,
        vacant_days=vacant_days,
    )
