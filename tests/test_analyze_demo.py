import pytest

from cost_of_vacancy.analyze import run_analysis
from cost_of_vacancy.benchmarks import VacancyBenchmarks
from cost_of_vacancy.demo_client import DemoCMSClient
from cost_of_vacancy.exceptions import AmbiguousHospitalError, HospitalNotFoundError


def test_run_analysis_matches_cardiologists_at_springfield():
    client = DemoCMSClient()
    result = run_analysis(
        client,
        hospital="Springfield General Hospital",
        specialty="Cardiology",
        vacant_days=365,
        benchmarks=VacancyBenchmarks(),
    )

    # 3 cardiologists affiliated with Springfield (CCN 999001) in the fixture
    # data -- the Riverside cardiologist (CCN 999002) and the two Springfield
    # family-practice NPIs must be excluded.
    assert result.matched_provider_count == 3
    assert result.hospital == "SPRINGFIELD GENERAL HOSPITAL"
    assert result.queried_hospital == "Springfield General Hospital"
    assert result.hospital_ccn == "999001"
    assert result.lost_revenue_component > 0
    assert result.total_cost_of_vacancy > result.lost_revenue_component


def test_run_analysis_family_practice_differs_from_cardiology():
    client = DemoCMSClient()
    cardiology = run_analysis(client, "Springfield General Hospital", "Cardiology", benchmarks=VacancyBenchmarks())
    family_practice = run_analysis(client, "Springfield General Hospital", "Family Practice", benchmarks=VacancyBenchmarks())

    assert family_practice.matched_provider_count == 2
    assert family_practice.avg_medicare_allowed_per_provider < cardiology.avg_medicare_allowed_per_provider
    assert family_practice.total_cost_of_vacancy < cardiology.total_cost_of_vacancy


def test_run_analysis_riverside_only_finds_its_own_cardiologist():
    client = DemoCMSClient()
    result = run_analysis(client, "Riverside Medical Center", "Cardiology", benchmarks=VacancyBenchmarks())
    assert result.hospital_ccn == "999002"
    assert result.matched_provider_count == 1


def test_run_analysis_unknown_hospital_raises_not_found():
    client = DemoCMSClient()
    with pytest.raises(HospitalNotFoundError):
        run_analysis(client, "Nonexistent Hospital", "Cardiology", benchmarks=VacancyBenchmarks())


def test_run_analysis_ambiguous_hospital_name_raises():
    client = DemoCMSClient()
    # A generic query with no distinguishing tokens against either fixture
    # hospital should not silently pick one.
    with pytest.raises((HospitalNotFoundError, AmbiguousHospitalError)):
        run_analysis(client, "Hospital", "Cardiology", benchmarks=VacancyBenchmarks())


def test_run_analysis_state_filter_narrows_the_query():
    client = DemoCMSClient()
    result = run_analysis(client, "Springfield General Hospital", "Cardiology", state="IL", benchmarks=VacancyBenchmarks())
    assert result.hospital_ccn == "999001"

    with pytest.raises(HospitalNotFoundError):
        run_analysis(client, "Springfield General Hospital", "Cardiology", state="CA", benchmarks=VacancyBenchmarks())
