"""Command-line entry point.

    python -m cost_of_vacancy.cli --hospital "Springfield General Hospital" --specialty "Cardiology" --demo

Drop --demo to hit the live CMS API instead of bundled sample data.
"""
import argparse
import json
import sys

from .analyze import run_analysis
from .benchmarks import VacancyBenchmarks


def build_parser():
    p = argparse.ArgumentParser(
        prog="cost-of-vacancy",
        description="Estimate the annual cost of a vacant specialty position at a hospital, using CMS Medicare billing data plus configurable staffing-cost assumptions.",
    )
    p.add_argument("--hospital", required=True, help="Hospital name as it would appear in CMS facility data, e.g. 'Springfield General Hospital'.")
    p.add_argument("--specialty", required=True, help="Specialty as it would appear in CMS provider-type data, e.g. 'Cardiology'.")
    p.add_argument("--vacant-days", type=int, default=365, help="Number of days the position is vacant (default: 365, i.e. a full year).")

    p.add_argument("--medicare-payer-share", type=float, default=None, help="Assumed share of hospital revenue that is Medicare fee-for-service, used to gross up Medicare billings to an all-payer estimate (default: 0.40).")
    p.add_argument("--contribution-margin", type=float, default=None, help="Share of foregone revenue actually lost as margin, 0-1 (default: 1.0).")
    p.add_argument("--locum-daily-rate", type=float, default=None, help="Override the per-day interim/locum coverage rate for this specialty.")
    p.add_argument("--recruitment-cost", type=float, default=None, help="Override the one-time recruitment cost for this specialty.")

    p.add_argument("--facility-dataset-id", default=None, help="Override the CMS Facility Affiliation dataset id.")
    p.add_argument("--specialty-dataset-id", default=None, help="Override the CMS National Downloadable File dataset id.")
    p.add_argument("--utilization-dataset-id", default=None, help="Override the CMS Medicare Physician & Other Practitioners by Provider dataset id.")

    p.add_argument("--demo", action="store_true", help="Use bundled sample data instead of calling the live CMS API (useful for trying the tool offline).")
    p.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of a formatted report.")
    return p


def _build_client(demo):
    if demo:
        from .demo_client import DemoCMSClient
        return DemoCMSClient()
    from .cms_client import CMSClient
    return CMSClient()


def _build_benchmarks(args):
    benchmarks = VacancyBenchmarks()
    if args.medicare_payer_share is not None:
        benchmarks.medicare_payer_share = args.medicare_payer_share
    if args.contribution_margin is not None:
        benchmarks.contribution_margin_pct = args.contribution_margin
    if args.locum_daily_rate is not None:
        benchmarks.default_locum_daily_rate = args.locum_daily_rate
        benchmarks.locum_daily_rate_by_specialty[args.specialty.lower()] = args.locum_daily_rate
    if args.recruitment_cost is not None:
        benchmarks.default_recruitment_cost = args.recruitment_cost
        benchmarks.recruitment_cost_by_specialty[args.specialty.lower()] = args.recruitment_cost
    return benchmarks


def format_report(result):
    d = result.to_dict()
    lines = [
        f"Cost of Vacancy: {d['specialty']} at {d['hospital']}",
        f"  Vacant period:                        {d['vacant_days']} days",
        f"  CMS-matched clinicians used for basis: {d['matched_provider_count']}",
        "",
        "  Estimate basis (from CMS Medicare billing data):",
        f"    Avg Medicare-allowed amount/provider:  ${d['avg_medicare_allowed_per_provider']:,.2f}",
        f"    Avg Medicare payment/provider:         ${d['avg_medicare_payment_per_provider']:,.2f}",
        f"    Est. all-payer annual revenue/provider:${d['estimated_annual_allpayer_revenue_per_provider']:,.2f}",
        "",
        "  Cost components:",
        f"    Lost patient revenue:    ${d['lost_revenue_component']:,.2f}",
        f"    Interim/locum coverage:  ${d['locum_coverage_component']:,.2f}",
        f"    Recruitment:             ${d['recruitment_component']:,.2f}",
        "  " + "-" * 40,
        f"    TOTAL COST OF VACANCY:   ${d['total_cost_of_vacancy']:,.2f}",
        "",
        "  Note: lost-revenue is a lower-bound proxy from Medicare Part B billings only;",
        "  locum/recruitment figures are editable assumptions, not CMS data.",
        "  See --help for override flags.",
    ]
    if d["matched_provider_count"] == 0:
        lines.insert(3, "  WARNING: no matching clinicians found in CMS data for this hospital/specialty --")
        lines.insert(4, "  the lost-revenue component is $0 and only the benchmark components are populated.")
        lines.insert(5, "  Check the hospital/specialty spelling, or pass --facility-dataset-id / --specialty-dataset-id.")
    return "\n".join(lines)


def main(argv=None):
    args = build_parser().parse_args(argv)
    client = _build_client(args.demo)
    benchmarks = _build_benchmarks(args)

    result = run_analysis(
        client,
        hospital=args.hospital,
        specialty=args.specialty,
        vacant_days=args.vacant_days,
        benchmarks=benchmarks,
        facility_dataset_id=args.facility_dataset_id,
        specialty_dataset_id=args.specialty_dataset_id,
        utilization_dataset_id=args.utilization_dataset_id,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
