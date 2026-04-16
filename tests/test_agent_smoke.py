from __future__ import annotations

import unittest
from unittest.mock import patch

from job_agent.agent import CompanyJobAgent, ResumeProfile, _normalize_careers_url
from job_agent.collectors.walmart import WalmartCollector


class FakePage:
    def __init__(self, href_sequences: list[list[str]]):
        self.href_sequences = href_sequences
        self.goto_calls: list[str] = []
        self._idx = 0
        self.mouse = self

    def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        self.goto_calls.append(url)

    def wait_for_timeout(self, ms: int) -> None:
        return None

    def wheel(self, x: int, y: int) -> None:
        return None

    def eval_on_selector_all(self, selector: str, script: str):
        if "({text:" in script:
            return [{"text": "", "href": ""}]
        value = self.href_sequences[min(self._idx, len(self.href_sequences) - 1)]
        self._idx += 1
        return value


class UrlValidationTests(unittest.TestCase):
    def test_normalize_careers_url_accepts_valid(self) -> None:
        normalized = _normalize_careers_url("careers.walmart.com/us/en/results?searchQuery=software")
        self.assertEqual(
            normalized,
            "https://careers.walmart.com/us/en/results?searchQuery=software",
        )

    def test_normalize_careers_url_rejects_invalid(self) -> None:
        with self.assertRaises(ValueError):
            _normalize_careers_url("First DNUM call right after startup: HTTP 000")


class WalmartCollectorTests(unittest.TestCase):
    def test_collect_role_links_careers_filters_job_urls(self) -> None:
        collector = WalmartCollector(
            results_url="https://careers.walmart.com/us/en/results?searchQuery=software",
            max_pages=1,
        )
        page = FakePage(
            href_sequences=[
                [
                    "https://careers.walmart.com/us/en/jobs/R-2414965",
                    "https://careers.walmart.com/us/en/about",
                    "https://careers.walmart.com/us/en/jobs/R-9999999",
                ]
            ]
        )
        links = collector._collect_role_links(page)
        self.assertEqual(
            links,
            [
                "https://careers.walmart.com/us/en/jobs/R-2414965",
                "https://careers.walmart.com/us/en/jobs/R-9999999",
            ],
        )

    def test_collect_role_links_workday_filters_job_urls(self) -> None:
        collector = WalmartCollector(
            results_url="https://walmart.wd5.myworkdayjobs.com/WalmartExternal",
            max_pages=1,
        )
        page = FakePage(
            href_sequences=[
                [
                    "https://walmart.wd5.myworkdayjobs.com/WalmartExternal/job/a/b_R-123",
                    "https://walmart.wd5.myworkdayjobs.com/WalmartExternal/search",
                ]
            ]
        )
        links = collector._collect_role_links(page)
        self.assertEqual(
            links,
            ["https://walmart.wd5.myworkdayjobs.com/WalmartExternal/job/a/b_R-123"],
        )


class AgentExperienceTests(unittest.TestCase):
    def test_experience_filtering_keeps_matching_roles(self) -> None:
        from job_agent.matcher.models import JobPosting, MatchResult, RankedJob

        agent = CompanyJobAgent()
        ranked = [
            RankedJob(
                job=JobPosting(title="Backend Engineer", description="Requires 3 years experience", company="Walmart"),
                match=MatchResult(score=90, level="strong", should_apply=True, hard_skip=False),
                rank_score=90.0,
                bucket="apply_now",
            ),
            RankedJob(
                job=JobPosting(title="Staff Engineer", description="Requires 10 years experience", company="Walmart"),
                match=MatchResult(score=85, level="strong", should_apply=True, hard_skip=False),
                rank_score=85.0,
                bucket="apply_now",
            ),
        ]

        filtered = agent._filter_experience_fit(ranked, ResumeProfile(years_experience=5))
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].job.title, "Backend Engineer")


class DirectUrlCollectorTests(unittest.TestCase):
    def test_walmart_direct_job_url_short_circuit(self) -> None:
        collector = WalmartCollector(results_url="https://careers.walmart.com/us/en/jobs/R-2414965", max_pages=3)
        page = FakePage(href_sequences=[["https://example.com"]])
        self.assertEqual(collector._collect_role_links(page), ["https://careers.walmart.com/us/en/jobs/R-2414965"])
        self.assertEqual(page.goto_calls, [])

    def test_goldman_direct_role_url_short_circuit(self) -> None:
        from job_agent.collectors.goldman_sachs import GoldmanSachsCollector

        collector = GoldmanSachsCollector(results_url="https://higher.gs.com/roles/166054", max_pages=3)
        page = FakePage(href_sequences=[["https://example.com"]])
        self.assertEqual(collector._collect_role_links(page), ["https://higher.gs.com/roles/166054"])
        self.assertEqual(page.goto_calls, [])


class AgentUrlInferenceTests(unittest.TestCase):
    def test_agent_infers_walmart_collector_from_hostname(self) -> None:
        agent = CompanyJobAgent()
        with patch("job_agent.collectors.walmart.WalmartCollector.collect", return_value=[] ) as mocked:
            jobs = agent.collect_jobs(
                company_name="unknown-company",
                careers_url="https://careers.walmart.com/us/en/results?searchQuery=software",
                max_pages=1,
                max_jobs=5,
                headless=True,
            )
        self.assertEqual(jobs, [])
        self.assertTrue(mocked.called)


if __name__ == "__main__":
    unittest.main()
