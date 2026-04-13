# Walmart job-search improvement workflow

Use this skill when improving Walmart job-search coverage in this repository.

## Goals

1. Make Walmart Workday collection reliable.
2. Prefer backend, platform, distributed systems, cloud, and Java/Python roles.
3. Treat unclear sponsorship as manual review, not blind apply.
4. Never implement auto-submit without an explicit safe stop before final submission.

## Standard task checklist

- Inspect `job_agent/collectors/walmart.py`.
- Run the Walmart collector on a small sample.
- Fix brittle selectors if collection returns zero jobs.
- Validate that `JobSearchPipeline` ranks backend/platform roles above frontend-heavy roles.
- Keep changes small, tested, and easy to review.

## Prompts to use in Codex Cloud

- Improve Walmart Workday link extraction and add defensive selectors.
- Add export of ranked Walmart jobs to JSON.
- Add tests for sponsorship handling when the job description is silent.
- Refactor Goldman and Walmart collectors to share a reusable Workday-style base class where possible.
