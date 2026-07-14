import pytest

from cost_of_vacancy.analyze import run_analysis
from cost_of_vacancy.benchmarks import VacancyBenchmarks
from cost_of_vacancy.demo_client import DemoCMSClient


def test_run_analysis_matches_cardiologists_at_springfield():
    client = DemoCMSClient()
    result = run_analysis(
        client,
        hospital="Springfield General Hospital",
        specialty="Cardiology",
        vacant_days=365,
        benchmarks=VacancyBenchmarks(),
    )

    # 3 cardiologists affiliated with Springfield in the fixture data,
    # the Riverside cardiologist and the two Springfield family-practice
    # NPIs must be excluded.
    assert result.matched_provider_count == 3
    assert result.lost_revenue_component > 0
    assert result.total_cost_of_vacancy > result.lost_revenue_component


def test_run_analysis_family_practice_differs_from_cardiology():
    client = DemoCMSClient()
    cardiology = run_analysis(client, "Springfield General Hospital", "Cardiology", benchmarks=VacancyBenchmarks())
    family_practice = run_analysis(client, "Springfield General Hospital", "Family Practice", benchmarks=VacancyBenchmarks())

    assert family_practice.matched_provider_count == 2
    assert family_practice.avg_medicare_allowed_per_provider < cardiology.avg_medicare_allowed_per_provider
    assert family_practice.total_cost_of_vacancy < cardiology.total_cost_of_vacancy


def test_run_analysis_unknown_hospital_returns_zero_matches_not_an_error():
    client = DemoCMSClient()
    result = run_analysis(client, "Nonexistent Hospital", "Cardiology", benchmarks=VacancyBenchmarks())
    assert result.matched_provider_count == 0
    assert result.lost_revenue_component == 0.0
    assert result.total_cost_of_vacancy > 0  # benchmark components still apply
