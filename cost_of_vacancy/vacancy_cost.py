"""Core cost-of-vacancy calculation.

Total annual cost of vacancy = lost revenue + interim coverage cost +
recruitment cost, where:

* **Lost revenue** is estimated from CMS Medicare billing data for
  clinicians of the target specialty at the target hospital: their average
  Medicare-allowed amount is grossed up to an all-payer estimate using
  `VacancyBenchmarks.medicare_payer_share`, pro-rated across the vacant
  period, and scaled by `contribution_margin_pct`.
* **Interim coverage cost** is a locum/overtime day-rate benchmark times
  the number of vacant days.
* **Recruitment cost** is a one-time benchmark cost to fill the role.

This is a lower-bound, Part-B-billing-only proxy: it doesn't capture
downstream hospital revenue a physician drives (referrals, facility fees,
ancillary services), which for many specialties dwarfs their own
professional billings. Treat the output as directional, not exact.
"""
from dataclasses import dataclass
from statistics import mean


@dataclass
class VacancyCostResult:
    hospital: str
    specialty: str
    vacant_days: int
    matched_provider_count: int
    avg_medicare_payment_per_provider: float
    avg_medicare_allowed_per_provider: float
    estimated_annual_allpayer_revenue_per_provider: float
    lost_revenue_component: float
    locum_coverage_component: float
    recruitment_component: float

    @property
    def total_cost_of_vacancy(self):
        return self.lost_revenue_component + self.locum_coverage_component + self.recruitment_component

    def to_dict(self):
        return {
            "hospital": self.hospital,
            "specialty": self.specialty,
            "vacant_days": self.vacant_days,
            "matched_provider_count": self.matched_provider_count,
            "avg_medicare_payment_per_provider": round(self.avg_medicare_payment_per_provider, 2),
            "avg_medicare_allowed_per_provider": round(self.avg_medicare_allowed_per_provider, 2),
            "estimated_annual_allpayer_revenue_per_provider": round(self.estimated_annual_allpayer_revenue_per_provider, 2),
            "lost_revenue_component": round(self.lost_revenue_component, 2),
            "locum_coverage_component": round(self.locum_coverage_component, 2),
            "recruitment_component": round(self.recruitment_component, 2),
            "total_cost_of_vacancy": round(self.total_cost_of_vacancy, 2),
        }


def compute_cost_of_vacancy(hospital, specialty, provider_financials, benchmarks, vacant_days=365):
    """`provider_financials` is a list of dicts as returned by
    `provider_utilization.fetch_provider_financials` (each with at least
    `medicare_payment` and `medicare_allowed` keys). An empty list is valid
    input -- it means CMS billing data couldn't ground the revenue estimate,
    so `lost_revenue_component` comes out as 0 while the benchmark-driven
    locum/recruitment components are still computed.
    """
    if vacant_days < 0:
        raise ValueError("vacant_days must be >= 0")

    if provider_financials:
        avg_payment = mean(p.get("medicare_payment", 0.0) for p in provider_financials)
        avg_allowed = mean(p.get("medicare_allowed", 0.0) for p in provider_financials)
    else:
        avg_payment = 0.0
        avg_allowed = 0.0

    base_annual_medicare_revenue = avg_allowed or avg_payment
    payer_share = benchmarks.medicare_payer_share or 1.0
    allpayer_annual_revenue = base_annual_medicare_revenue / payer_share

    daily_revenue = allpayer_annual_revenue / 365.0
    lost_revenue = daily_revenue * vacant_days * benchmarks.contribution_margin_pct

    locum_cost = benchmarks.locum_daily_rate(specialty) * vacant_days
    recruitment_cost = benchmarks.recruitment_cost(specialty) if vacant_days > 0 else 0.0

    return VacancyCostResult(
        hospital=hospital,
        specialty=specialty,
        vacant_days=vacant_days,
        matched_provider_count=len(provider_financials),
        avg_medicare_payment_per_provider=avg_payment,
        avg_medicare_allowed_per_provider=avg_allowed,
        estimated_annual_allpayer_revenue_per_provider=allpayer_annual_revenue,
        lost_revenue_component=lost_revenue,
        locum_coverage_component=locum_cost,
        recruitment_component=recruitment_cost,
    )
