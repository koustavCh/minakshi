from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse
import re

from job_agent.collectors.goldman_sachs import GoldmanSachsCollector
from job_agent.collectors.walmart import WalmartCollector
from job_agent.matcher.models import JobPosting, PipelineOutput, RankedJob
from job_agent.matcher.pipeline import JobSearchPipeline
from job_agent.matcher.policy import load_policy


CollectorFactory = Callable[[str, int, int, bool], object]


def _normalize_company_name(company_name: str) -> str:
    return " ".join(company_name.lower().split())


def _extract_required_years(text: str) -> Optional[int]:
    matches = re.findall(r"(\d{1,2})\s*\+?\s*(?:years|year|yrs|yr)", text, flags=re.IGNORECASE)
    if not matches:
        return None
    return max(int(m) for m in matches)


@dataclass
class ResumeProfile:
    years_experience: int


class CompanyJobAgent:
    """
    Orchestrates collection + ranking with a simple company-name interface.

    Current collector coverage:
    - Walmart careers (Workday)
    - Goldman Sachs careers
    """

    def __init__(self) -> None:
        self.policy = load_policy()
        self.collectors: Dict[str, CollectorFactory] = {
            "walmart": lambda url, max_pages, max_jobs, headless: WalmartCollector(
                results_url=url,
                max_pages=max_pages,
                max_jobs=max_jobs,
                headless=headless,
                company_name="Walmart",
            ),
            "goldman sachs": lambda url, max_pages, max_jobs, headless: GoldmanSachsCollector(
                results_url=url,
                max_pages=max_pages,
                max_jobs=max_jobs,
                headless=headless,
            ),
            "goldman": lambda url, max_pages, max_jobs, headless: GoldmanSachsCollector(
                results_url=url,
                max_pages=max_pages,
                max_jobs=max_jobs,
                headless=headless,
            ),
        }

    def collect_and_rank(
        self,
        company_name: str,
        careers_url: str,
        resume_profile: ResumeProfile,
        max_pages: int = 1,
        max_jobs: int = 20,
        headless: bool = True,
    ) -> Tuple[List[RankedJob], PipelineOutput]:
        jobs = self.collect_jobs(
            company_name=company_name,
            careers_url=careers_url,
            max_pages=max_pages,
            max_jobs=max_jobs,
            headless=headless,
        )

        search_strategy = self.policy.get("search_strategy", {})
        exploratory_ratio = float(search_strategy.get("exploratory_ratio", 0.30))
        output = JobSearchPipeline(
            exploratory_ratio=exploratory_ratio,
            max_per_company=max_jobs,
            deduplicate_similar_titles=True,
        ).run(jobs)

        all_ranked_jobs = output.apply_now + output.manual_review
        experience_qualified = self._filter_experience_fit(all_ranked_jobs, resume_profile)
        return experience_qualified, output

    def collect_jobs(
        self,
        company_name: str,
        careers_url: str,
        max_pages: int,
        max_jobs: int,
        headless: bool,
    ) -> List[JobPosting]:
        company_key = _normalize_company_name(company_name)
        factory = self.collectors.get(company_key)
        if factory:
            collector = factory(careers_url, max_pages, max_jobs, headless)
            return collector.collect()

        hostname = urlparse(careers_url).netloc.lower()
        if "myworkdayjobs.com" in hostname:
            generic_workday = WalmartCollector(
                results_url=careers_url,
                max_pages=max_pages,
                max_jobs=max_jobs,
                headless=headless,
                company_name=company_name,
            )
            return generic_workday.collect()

        supported = ", ".join(sorted(self.collectors.keys()))
        raise ValueError(
            f"Unsupported company/url combination for '{company_name}'. Supported companies: {supported}. "
            "For generic fallback, provide a Workday careers URL."
        )

    def _filter_experience_fit(self, ranked_jobs: List[RankedJob], resume_profile: ResumeProfile) -> List[RankedJob]:
        matched: List[RankedJob] = []
        for ranked in ranked_jobs:
            required = _extract_required_years(f"{ranked.job.title} {ranked.job.description}")
            if required is None or required <= resume_profile.years_experience:
                matched.append(ranked)
        return matched
