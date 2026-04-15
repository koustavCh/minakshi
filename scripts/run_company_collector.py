from __future__ import annotations

import sys
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[1]))

from job_agent.agent import CompanyJobAgent, ResumeProfile
from job_agent.application.profile import ApplicantProfile, load_profile_from_json
from job_agent.matcher.models import RankedJob
from job_agent.browser.playwright_apply import run_apply_session


def _read_int(prompt: str, default: int) -> int:
    raw = input(f"{prompt} [{default}]: ").strip()
    return int(raw) if raw else default


def _read_profile(default_years: int) -> ApplicantProfile:
    resume_json = input("Resume JSON path (optional, press Enter to skip): ").strip()
    if resume_json:
        profile = load_profile_from_json(resume_json)
        if profile.years_experience == 0:
            profile.years_experience = _read_int("Years of experience missing in JSON. Enter value", default_years)
        return profile

    years = _read_int("Your total years of experience", default_years)
    profile = ApplicantProfile(years_experience=years)
    profile.full_name = input("Full name (for application fill, optional): ").strip()
    profile.email = input("Email (optional): ").strip()
    profile.phone = input("Phone (optional): ").strip()
    profile.linkedin = input("LinkedIn URL (optional): ").strip()
    profile.github = input("GitHub URL (optional): ").strip()
    profile.location = input("Location (optional): ").strip()
    return profile


def _print_checkbox_list(jobs: List[RankedJob]) -> None:
    print("\n" + "=" * 100)
    print("RELEVANT ROLES (policy + resume experience)")
    print("Select roles by index, e.g. 1,3,5")
    print("=" * 100)
    for idx, ranked in enumerate(jobs, start=1):
        print(f"[ ] {idx}. {ranked.job.company} | {ranked.job.title}")
        print(f"    score={ranked.rank_score} | level={ranked.match.level} | location={ranked.job.location}")
        print(f"    apply_url={ranked.job.apply_url or ranked.job.source_url}")


def _parse_selected_indexes(raw: str, total: int) -> List[int]:
    if not raw.strip():
        return []
    indexes: List[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        value = int(token)
        if value < 1 or value > total:
            raise ValueError(f"Selection index out of range: {value}")
        indexes.append(value)
    return sorted(set(indexes))


def main() -> None:
    company_name = input("Enter company name (example: Walmart, Goldman Sachs): ").strip()
    careers_url = input("Enter careers/results URL: ").strip()

    if not company_name:
        raise ValueError("company name is required")
    if not careers_url:
        raise ValueError("careers URL is required")

    max_pages = _read_int("Max result pages to scan", 1)
    max_jobs = _read_int("Max jobs to parse", 20)
    raw_headless = input("Run browser in headless mode for collection? [y]: ").strip().lower()
    headless = raw_headless != "n"

    profile = _read_profile(default_years=5)

    agent = CompanyJobAgent()
    matched_jobs, output = agent.collect_and_rank(
        company_name=company_name,
        careers_url=careers_url,
        resume_profile=ResumeProfile(years_experience=profile.years_experience),
        max_pages=max_pages,
        max_jobs=max_jobs,
        headless=headless,
    )

    matched_jobs = sorted(matched_jobs, key=lambda r: r.rank_score, reverse=True)
    print("\n" + "=" * 100)
    print("COLLECTION SUMMARY")
    print("=" * 100)
    print(f"Collected jobs: {output.summary.get('total_jobs_seen', 0)}")
    print(f"Policy eligible (apply_now + manual_review): {len(output.apply_now) + len(output.manual_review)}")
    print(f"Resume-experience qualified: {len(matched_jobs)}")

    if not matched_jobs:
        print("No relevant roles found for current policy/profile.")
        return

    _print_checkbox_list(matched_jobs)
    selected_raw = input("\nEnter checked role indexes (comma separated), or Enter to stop: ")
    selected_indexes = _parse_selected_indexes(selected_raw, total=len(matched_jobs))

    if not selected_indexes:
        print("No roles selected. Exiting safely.")
        return

    print("\nStarting guided application fill for selected roles (submit disabled).")
    for index in selected_indexes:
        role = matched_jobs[index - 1]
        url = role.job.apply_url or role.job.source_url
        if not url:
            print(f"Skipping '{role.job.title}' because no apply/source URL is available.")
            continue
        print(f"\n--- Role {index}: {role.job.title} ---")
        run_apply_session(url=url, profile=profile, allow_submit=False, headless=False)


if __name__ == "__main__":
    main()
