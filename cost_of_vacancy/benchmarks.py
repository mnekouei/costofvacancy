"""Editable assumptions that turn CMS billing data into a full cost-of-
vacancy estimate.

CMS's provider-billing data only tells us what a specialty's clinicians
bill Medicare -- it says nothing about locum/temp coverage rates,
recruitment costs, or what share of a hospital's revenue comes from
Medicare versus other payers. Those pieces are unavoidably assumptions,
not measurements, so they live here as plain, overridable defaults rather
than being baked into the formula. The numbers below are order-of-magnitude
placeholders (loosely informed by publicly reported physician-recruiting
and locum-staffing surveys) -- treat them as a starting point to replace
with your own hospital's actual figures via CLI flags or by editing this
file, not as authoritative benchmarks.
"""
from dataclasses import dataclass, field


def _default_locum_daily_rates():
    return {
        "family practice": 1300.0,
        "internal medicine": 1400.0,
        "hospitalist": 1600.0,
        "emergency medicine": 1900.0,
        "psychiatry": 1500.0,
        "anesthesiology": 2200.0,
        "orthopedic surgery": 2800.0,
        "general surgery": 2500.0,
        "cardiology": 2400.0,
        "radiology": 2000.0,
        "obstetrics/gynecology": 1900.0,
        "neurology": 1900.0,
        "pediatrics": 1300.0,
    }


def _default_recruitment_costs():
    return {
        "family practice": 25000.0,
        "internal medicine": 27000.0,
        "hospitalist": 28000.0,
        "emergency medicine": 30000.0,
        "psychiatry": 26000.0,
        "anesthesiology": 35000.0,
        "orthopedic surgery": 45000.0,
        "general surgery": 40000.0,
        "cardiology": 42000.0,
        "radiology": 32000.0,
        "obstetrics/gynecology": 30000.0,
        "neurology": 30000.0,
        "pediatrics": 24000.0,
    }


@dataclass
class VacancyBenchmarks:
    # Rough share of a hospital's patient revenue that comes from Medicare
    # fee-for-service (used to gross up Medicare-only billings to an
    # all-payer estimate). Override with your hospital's actual payer mix.
    medicare_payer_share: float = 0.40

    # Share of foregone revenue actually lost as margin (vs. variable cost
    # that would have been incurred anyway). 1.0 = full revenue counted.
    contribution_margin_pct: float = 1.0

    default_locum_daily_rate: float = 1600.0
    locum_daily_rate_by_specialty: dict = field(default_factory=_default_locum_daily_rates)

    default_recruitment_cost: float = 30000.0
    recruitment_cost_by_specialty: dict = field(default_factory=_default_recruitment_costs)

    def locum_daily_rate(self, specialty):
        return self.locum_daily_rate_by_specialty.get((specialty or "").strip().lower(), self.default_locum_daily_rate)

    def recruitment_cost(self, specialty):
        return self.recruitment_cost_by_specialty.get((specialty or "").strip().lower(), self.default_recruitment_cost)
