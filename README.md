# Cost of Vacancy

Estimates the annual cost of a vacant physician position for a given
**specialty** at a given **hospital**, using public CMS Medicare billing
data plus a small set of editable staffing-cost assumptions.

```
python -m cost_of_vacancy.cli --hospital "Springfield General Hospital" --specialty "Cardiology"
```

```
Cost of Vacancy: Cardiology at SPRINGFIELD GENERAL HOSPITAL
  (matched from query: 'Springfield General Hospital', CCN 999001)
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

The pipeline chains four CMS Provider Data Catalog / provider-summary
datasets, queried live via CMS's public APIs (verified against the real
endpoints -- see `scripts/diagnose_cms_api.py`):

1. **Hospital name -> CCN.** [Hospital General
   Information](https://data.cms.gov/provider-data/dataset/xubh-q36u)
   resolves the hospital name to its CMS Certification Number (CCN), via a
   fuzzy token-overlap match (see "Hospital matching" below).
2. **CCN -> affiliated clinician NPIs.** [Facility
   Affiliation](https://data.cms.gov/provider-data/dataset/27ea-46a8) has no
   hospital-name field at all -- only a CCN -- which is why step 1 has to
   happen first. It returns the NPIs (National Provider Identifiers) of
   clinicians affiliated with that CCN.
3. **Filter to the specialty.** [National Downloadable
   File](https://data.cms.gov/provider-data/dataset/mj5m-pzi6) gives each
   NPI's primary specialty (`pri_spec`), used to narrow the affiliated
   clinicians down to the requested one.
4. **Pull their Medicare billings.** [Medicare Physician & Other
   Practitioners - by
   Provider](https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider)
   reports each matched clinician's total Medicare-allowed amount, Medicare
   payment, and submitted charges for the year.

Steps 1-3 use CMS's DKAN datastore query API
(`provider-data/api/1/datastore/query/{dataset-id}/0`) with server-side
`conditions[]` filtering -- required since Facility Affiliation and the
National Downloadable File each have 2-3 million rows, far too many to page
through client-side. Step 4 uses the newer `data-api/v1/dataset/{id}/data`
endpoint with `filter[Rndrng_NPI]=...`, whose dataset id CMS rotates on each
annual release, so it's resolved dynamically by title against
`data.cms.gov/data.json` rather than hardcoded.

**Turning billings into a full cost-of-vacancy estimate.** See
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

### Hospital matching

`--hospital` is matched against CMS's `facility_name` field by token
overlap (ignoring generic words like "hospital", "medical", "center").
If nothing scores highly enough, or if the top two candidates are too
close to call, the CLI exits with an error listing the candidates instead
of silently guessing -- pass `--state` (two-letter code) to disambiguate.
The report always prints which CCN/canonical name your query actually
resolved to, so check that before trusting the numbers.

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
- CMS suppresses low-volume/privacy-sensitive billing rows, and
  `--max-providers` caps how many matched clinicians are pulled (default
  25, to bound API calls) — so `matched_provider_count` may be smaller than
  the hospital's actual headcount for that specialty. Always sanity-check
  that number in the output before trusting the estimate.
- The Hospital General Information, Facility Affiliation, and National
  Downloadable File dataset ids (`xubh-q36u`, `27ea-46a8`, `mj5m-pzi6`) have
  been stable CMS Provider Data Catalog ids for years and are hardcoded;
  the physician-billing dataset id rotates yearly and is resolved
  dynamically instead. If CMS ever changes any of these, override with
  `--hospital-dataset-id` / `--facility-dataset-id` / `--specialty-dataset-id`
  / `--utilization-dataset-id`.

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
| `--state` | none | Two-letter state code to disambiguate similarly-named hospitals |
| `--vacant-days` | 365 | Length of the vacancy in days |
| `--max-providers` | 25 | Cap on matched clinicians used for the billing-data basis |
| `--medicare-payer-share` | 0.40 | Assumed Medicare share of hospital revenue |
| `--contribution-margin` | 1.0 | Share of foregone revenue actually lost as margin |
| `--locum-daily-rate` | specialty-dependent | Override interim coverage day rate |
| `--recruitment-cost` | specialty-dependent | Override one-time recruitment cost |
| `--hospital-dataset-id` | `xubh-q36u` | Pin the Hospital General Information dataset id |
| `--facility-dataset-id` | `27ea-46a8` | Pin the Facility Affiliation dataset id |
| `--specialty-dataset-id` | `mj5m-pzi6` | Pin the National Downloadable File dataset id |
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
  cms_client.py            HTTP client for both CMS API shapes: data-api/v1 (paged, dynamic
                            dataset-id resolution) and the DKAN datastore query API
                            (server-side conditions[] filtering)
  facility_affiliations.py hospital name -> CCN -> affiliated NPIs -> specialty-filtered NPIs
  provider_utilization.py  NPIs -> Medicare billing figures
  benchmarks.py            editable locum-rate / recruitment-cost / payer-mix assumptions
  vacancy_cost.py          pure calculation: billing figures + benchmarks -> VacancyCostResult
  analyze.py               orchestrates the above into one call
  exceptions.py            HospitalNotFoundError / AmbiguousHospitalError
  cli.py                   argparse CLI
  demo_client.py           offline fixture-backed client (same interface as CMSClient)
  fixtures/                sample data used by --demo and the test suite
tests/                     unit tests (all offline; `vacancy_cost` math + fuzzy matching +
                            end-to-end pipeline against demo_client + CLI)
scripts/
  diagnose_cms_api.py      one-off script used to reverse-engineer the real CMS API shapes
                            during development; not part of the runtime pipeline
```

## Testing

```
pip install pytest
pytest
```

All tests run offline against `demo_client.DemoCMSClient` and pure
calculation logic. The live CMS API integration itself was verified
manually against the real endpoints (see `scripts/diagnose_cms_api.py` and
its output) rather than by an automated live test, since there's no way to
reach `data.cms.gov` from every environment this might run in -- run the
CLI without `--demo` to exercise it for real.
