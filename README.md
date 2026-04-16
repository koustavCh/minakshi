# Job Application Agent MVP

This package is a local-first starter kit for a job-application copilot.

## What improved in this version

- Added a **Walmart Workday collector** for Walmart careers pages.
- Added **job identifiers and apply URLs** to the shared job model.
- Improved the scoring logic for **Walmart platform/backend roles**.
- Relaxed sponsorship handling for Walmart and Goldman Sachs to **manual review when unclear** instead of hard-skip.
- Added **Codex Cloud setup files** so you can delegate repo tasks in Codex Cloud.

## What it does today

- scores jobs against your policy
- buckets roles into `apply_now`, `manual_review`, and `skip`
- keeps your matching rules in a JSON policy file
- supports CLI workflows with sample jobs
- includes Playwright browser scaffolds for future application automation
- includes collectors for **Goldman Sachs** and **Walmart**

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Run the Walmart collector

```bash
python scripts/run_walmart_collection.py
```

Suggested starting URL:

```text
https://walmart.wd5.myworkdayjobs.com/WalmartExternal
```

## Run the Goldman Sachs collector

```bash
python scripts/run_goldman_sachs_collection.py
```

## Run generic company collector (company + URL + resume years)

```bash
python scripts/run_company_collector.py
```

Sample resume profile JSON: `job_agent/config/resume_profile.sample.json`

Use this when you want to input:
- company name
- careers/results URL
- resume JSON path (optional) or manual profile fields

The agent will:
- collect roles using the company collector (with URL-based inference for Walmart careers, Goldman roles, and Workday URLs)
- accept direct job URLs (for example Walmart `/us/en/jobs/R-...`) as single-role collection inputs
- score with the existing policy
- return only policy-eligible roles that also fit your resume experience
- print a checkbox-style list so you can select which roles to apply for
- open each selected apply page, auto-fill known fields, ask clarifying questions when values are missing, and stop before submit

## Validate readiness gates

```bash
python scripts/validate_agent_readiness.py
```

Optional live gate:

```bash
python scripts/validate_agent_readiness.py \
  --live-company walmart \
  --live-url "https://careers.walmart.com/us/en/jobs/R-2414965" \
  --years 5
```

## Run sample ranking

```bash
python scripts/run_sample_pipeline.py
python scripts/test_walmart_known_roles.py
```

## Codex Cloud

1. Push this repo to GitHub.
2. Open Codex Cloud at ChatGPT Codex.
3. Connect the repository and configure the environment.
4. Start with the prompts in `.codex/skills/walmart-job-search/SKILL.md`.

## Suggested next upgrades

1. Persist collected jobs to SQLite.
2. Add a reusable Workday base collector.
3. Export ranked jobs to CSV or JSON for review.
4. Add a review dashboard.
5. Add safe browser automation that stops before submit.
