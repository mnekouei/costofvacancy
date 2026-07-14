# Cost of Vacancy

Estimates the annual cost of a vacant physician position for a given
**specialty** at a given **hospital**, using public CMS Medicare billing
data plus a small set of editable staffing-cost assumptions.

```
python -m cost_of_vacancy.cli --hospital "Springfield General Hospital" --specialty "Cardiology"
```

```
Cost of Vacancy: Cardiology at Springfield General Hospital
  Vacant period:                        365 days
  CMS-matched clinicians used for basis: 3

  Estimate basis (from CMS Medicare billing data):
    Avg Medicare-allowed amount/provider:  $299,333.33
    Avg Medicare payment/provider:         $239,333.33
    Est. all-payer annual revenue/provider:$748,333.33

  Cost components:
    Lost patient revenue:    $748,333.33
    Interim/locum coverage:  $876,000.00
    Recruitment:             $42,000.00
  ----------------------------------------
    TOTAL COST OF VACANCY:   $1,666,333.33
```

## How it works

1. **Find the clinicians.** Looks up the hospital in CMS's [Facility
   Affiliation](https://data.cms.gov/provider-data/dataset/27ea-46a8)
   dataset to get the NPIs (National Provider Identifiers) of clinicians
   affiliated with it, then narrows that list to the requested specialty
   using CMS's National Downloadable File.
2. **Pull their Medicare billings.** Looks up those NPIs in [Medicare
   Physician & Other Practitioners - by
   Provider](https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider),
   which reports each clinician's total Medicare-allowed amount, Medicare
   payment, and submitted charges for the year.
3. **Turn billings into a full cost-of-vacancy estimate.** See
   [`cost_of_vacancy/vacancy_cost.py`](cost_of_vacancy/vacancy_cost.py) and
   [`cost_of_vacancy/benchmarks.py`](cost_of_vacancy/benchmarks.py):

   ```
   total cost of vacancy = lost patient revenue + interim/locum coverage + recruitment cost
   ```

   - **Lost patient revenue**: the matched clinicians' average
     Medicare-allowed amount, grossed up to an all-payer estimate via
     `--medicare-payer-share` (default 0.40 — i.e. assumes Medicare is ~40%
     of the hospital's payer mix), pro-rated across `--vacant-days`, and
     scaled by `--contribution-margin` (default 1.0).
   - **Interim/locum coverage**: a per-day benchmark rate for temporary
     coverage of that specialty × `--vacant-days`.
   - **Recruitment**: a one-time benchmark cost to fill the role.

### Important limitations

- CMS's provider-billing dataset only covers **Medicare fee-for-service
  professional billings**. It does not capture private-payer revenue,
  Medicare Advantage, or the downstream hospital revenue a physician drives
  (referrals, facility fees, ancillary testing, OR time) — which for many
  specialties is larger than their own billings. Treat the lost-revenue
  figure as a **lower-bound proxy**, not a full financial-impact number.
- The locum-coverage and recruitment-cost numbers in `benchmarks.py` are
  **illustrative placeholders**, not verified market data. Override them
  with your own hospital's actual contracted locum rates and recruiting
  costs via `--locum-daily-rate` / `--recruitment-cost`, or edit
  `benchmarks.py` directly.
- Hospital/specialty name matching against CMS records is fuzzy
  (token-overlap), and CMS suppresses low-volume/privacy-sensitive rows —
  so `matched_provider_count` may be smaller than the hospital's actual
  headcount for that specialty. Always sanity-check that number in the
  output before trusting the estimate.
- CMS re-publishes these datasets annually with new dataset ids; this tool
  resolves the current id by title against CMS's live catalog
  (`data.cms.gov/data.json`) rather than hardcoding one, but if CMS renames
  a dataset you can always pin the id explicitly with
  `--facility-dataset-id` / `--specialty-dataset-id` / `--utilization-dataset-id`.

## Install

```
pip install -r requirements.txt
```

No API key is required — data.cms.gov's provider datasets are open.

## Usage

```
python -m cost_of_vacancy.cli --hospital "<hospital name>" --specialty "<specialty>" [options]
```

| Flag | Default | Meaning |
|---|---|---|
| `--vacant-days` | 365 | Length of the vacancy in days |
| `--medicare-payer-share` | 0.40 | Assumed Medicare share of hospital revenue |
| `--contribution-margin` | 1.0 | Share of foregone revenue actually lost as margin |
| `--locum-daily-rate` | specialty-dependent | Override interim coverage day rate |
| `--recruitment-cost` | specialty-dependent | Override one-time recruitment cost |
| `--facility-dataset-id` | resolved from CMS catalog | Pin the Facility Affiliation dataset id |
| `--specialty-dataset-id` | resolved from CMS catalog | Pin the National Downloadable File dataset id |
| `--utilization-dataset-id` | resolved from CMS catalog | Pin the Medicare Physician & Other Practitioners dataset id |
| `--json` | off | Print machine-readable JSON |
| `--demo` | off | Use bundled sample data instead of the live CMS API (no network needed) |

Try it without any network access first:

```
python -m cost_of_vacancy.cli --hospital "Springfield General Hospital" --specialty "Cardiology" --demo
```

## Project layout

```
cost_of_vacancy/
  cms_client.py            generic paging JSON client for data.cms.gov's data-api/v1
  facility_affiliations.py hospital name -> matching NPIs -> specialty-filtered NPIs
  provider_utilization.py  NPIs -> Medicare billing figures
  benchmarks.py            editable locum-rate / recruitment-cost / payer-mix assumptions
  vacancy_cost.py          pure calculation: billing figures + benchmarks -> VacancyCostResult
  analyze.py               orchestrates the above into one call
  cli.py                   argparse CLI
  demo_client.py           offline fixture-backed client (same interface as CMSClient)
  fixtures/                sample data used by --demo and the test suite
tests/                     unit tests (all offline; `vacancy_cost` math + fuzzy matching +
                            end-to-end pipeline against demo_client + CLI)
```

## Testing

```
pip install pytest
pytest
```

All tests run offline against `demo_client.DemoCMSClient` and pure
calculation logic — no network access is needed to verify the tool's math
and pipeline wiring. The live CMS API integration
(`cms_client.py`/`facility_affiliations.py`/`provider_utilization.py`) is
exercised by actually running the CLI against data.cms.gov (drop `--demo`).
