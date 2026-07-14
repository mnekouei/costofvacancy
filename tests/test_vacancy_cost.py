import pytest

from cost_of_vacancy.benchmarks import VacancyBenchmarks
from cost_of_vacancy.vacancy_cost import compute_cost_of_vacancy


def test_full_year_vacancy_with_matched_providers():
    benchmarks = VacancyBenchmarks(medicare_payer_share=0.5, contribution_margin_pct=1.0)
    financials = [
        {"medicare_payment": 200000.0, "medicare_allowed": 250000.0},
        {"medicare_payment": 180000.0, "medicare_allowed": 230000.0},
    ]

    result = compute_cost_of_vacancy(
        hospital="Springfield General Hospital",
        specialty="Cardiology",
        provider_financials=financials,
        benchmarks=benchmarks,
        vacant_days=365,
    )

    assert result.matched_provider_count == 2
    assert result.avg_medicare_allowed_per_provider == pytest.approx(240000.0)
    # grossed up from Medicare-only ($240k) to all-payer at 50% payer share
    assert result.estimated_annual_allpayer_revenue_per_provider == pytest.approx(480000.0)
    # full year at full margin => lost revenue equals the annual all-payer estimate
    assert result.lost_revenue_component == pytest.approx(480000.0, rel=1e-6)
    assert result.locum_coverage_component == pytest.approx(benchmarks.locum_daily_rate("Cardiology") * 365)
    assert result.recruitment_component == pytest.approx(benchmarks.recruitment_cost("Cardiology"))
    assert result.total_cost_of_vacancy == pytest.approx(
        result.lost_revenue_component + result.locum_coverage_component + result.recruitment_component
    )


def test_partial_year_vacancy_scales_lost_revenue_and_locum_linearly():
    benchmarks = VacancyBenchmarks(medicare_payer_share=0.4, contribution_margin_pct=1.0)
    financials = [{"medicare_payment": 100000.0, "medicare_allowed": 146000.0}]

    full_year = compute_cost_of_vacancy("H", "Family Practice", financials, benchmarks, vacant_days=365)
    half_year = compute_cost_of_vacancy("H", "Family Practice", financials, benchmarks, vacant_days=182)

    assert half_year.lost_revenue_component == pytest.approx(full_year.lost_revenue_component * (182 / 365), rel=1e-6)
    assert half_year.locum_coverage_component == pytest.approx(full_year.locum_coverage_component * (182 / 365), rel=1e-6)
    # recruitment is a one-time cost, not scaled by duration
    assert half_year.recruitment_component == pytest.approx(full_year.recruitment_component)


def test_contribution_margin_scales_lost_revenue_only():
    benchmarks_full = VacancyBenchmarks(medicare_payer_share=0.4, contribution_margin_pct=1.0)
    benchmarks_half_margin = VacancyBenchmarks(medicare_payer_share=0.4, contribution_margin_pct=0.5)
    financials = [{"medicare_payment": 100000.0, "medicare_allowed": 146000.0}]

    full = compute_cost_of_vacancy("H", "Family Practice", financials, benchmarks_full, vacant_days=365)
    half_margin = compute_cost_of_vacancy("H", "Family Practice", financials, benchmarks_half_margin, vacant_days=365)

    assert half_margin.lost_revenue_component == pytest.approx(full.lost_revenue_component * 0.5, rel=1e-6)
    assert half_margin.locum_coverage_component == pytest.approx(full.locum_coverage_component)


def test_no_matched_providers_zeroes_out_lost_revenue_but_keeps_benchmarks():
    benchmarks = VacancyBenchmarks()

    result = compute_cost_of_vacancy(
        hospital="Unknown Hospital",
        specialty="Cardiology",
        provider_financials=[],
        benchmarks=benchmarks,
        vacant_days=365,
    )

    assert result.matched_provider_count == 0
    assert result.lost_revenue_component == 0.0
    assert result.locum_coverage_component > 0
    assert result.recruitment_component > 0
    assert result.total_cost_of_vacancy == pytest.approx(
        result.locum_coverage_component + result.recruitment_component
    )


def test_falls_back_to_medicare_payment_when_allowed_amount_missing():
    benchmarks = VacancyBenchmarks(medicare_payer_share=1.0)
    financials = [{"medicare_payment": 90000.0, "medicare_allowed": 0.0}]

    result = compute_cost_of_vacancy("H", "Specialty", financials, benchmarks, vacant_days=365)

    assert result.avg_medicare_allowed_per_provider == 0.0
    assert result.estimated_annual_allpayer_revenue_per_provider == pytest.approx(90000.0)


def test_unknown_specialty_uses_default_benchmark_rates():
    benchmarks = VacancyBenchmarks()
    result = compute_cost_of_vacancy("H", "Some Rare Subspecialty", [], benchmarks, vacant_days=365)
    assert result.locum_coverage_component == pytest.approx(benchmarks.default_locum_daily_rate * 365)
    assert result.recruitment_component == pytest.approx(benchmarks.default_recruitment_cost)


def test_negative_vacant_days_rejected():
    with pytest.raises(ValueError):
        compute_cost_of_vacancy("H", "Cardiology", [], VacancyBenchmarks(), vacant_days=-1)
