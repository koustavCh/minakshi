from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
import json
import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from job_agent.matcher.models import JobPosting


WHITESPACE_RE = re.compile(r"\s+")
WORKDAY_JOB_RE = re.compile(r"/job/.+?_(R-[0-9-]+)")
CAREERS_JOB_RE = re.compile(r"/us/en/jobs/(R-[0-9-]+)", flags=re.IGNORECASE)


def clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def uniq_preserve_order(items: List[str]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def next_page_url(current_url: str, next_page: int) -> str:
    parsed = urlparse(current_url)
    params = parse_qs(parsed.query)
    params["page"] = [str(next_page)]
    query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=query))


@dataclass
class WalmartCollector:
    results_url: str = "https://walmart.wd5.myworkdayjobs.com/WalmartExternal"
    max_pages: int = 1
    max_jobs: int = 20
    headless: bool = True
    company_name: str = "Walmart"

    def collect(self) -> List[JobPosting]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.set_default_timeout(45000)
            role_links = self._collect_role_links(page)
            jobs: List[JobPosting] = []
            for link in role_links[: self.max_jobs]:
                job = self._parse_role_page(browser, link)
                if job:
                    jobs.append(job)
            browser.close()
            return jobs

    def _collect_role_links(self, page) -> List[str]:
        parsed = urlparse(self.results_url)
        hostname = parsed.netloc.lower()

        if "careers.walmart.com" in hostname:
            return self._collect_careers_role_links(page)
        return self._collect_workday_role_links(page)

    def _collect_workday_role_links(self, page) -> List[str]:
        collected: List[str] = []
        for page_num in range(self.max_pages):
            current_url = next_page_url(self.results_url, page_num + 1) if page_num > 0 else self.results_url
            page.goto(current_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            for _ in range(8):
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(800)
            hrefs = page.eval_on_selector_all(
                "a",
                """elements => elements.map(e => e.href).filter(Boolean)""",
            )
            candidates = [href for href in hrefs if "/job/" in href and "myworkdayjobs.com" in href]
            if not candidates:
                candidates = page.eval_on_selector_all(
                    "[data-automation-id='jobTitle'] a",
                    """elements => elements.map(e => e.href).filter(Boolean)""",
                )
            collected.extend(candidates)
            collected = uniq_preserve_order([link for link in collected if "/job/" in link])
        return collected

    def _collect_careers_role_links(self, page) -> List[str]:
        collected: List[str] = []
        current_url = self.results_url
        for _ in range(self.max_pages):
            page.goto(current_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            for _ in range(12):
                page.mouse.wheel(0, 2400)
                page.wait_for_timeout(600)

            hrefs = page.eval_on_selector_all("a", """elements => elements.map(e => e.href).filter(Boolean)""")
            candidates = []
            for href in hrefs:
                if "/us/en/jobs/" in href:
                    candidates.append(href)
            collected.extend(candidates)
            collected = uniq_preserve_order(collected)

            next_url = self._find_next_page_url(page)
            if not next_url or next_url == current_url:
                break
            current_url = next_url

        return collected

    def _find_next_page_url(self, page) -> str:
        hrefs = page.eval_on_selector_all(
            "a",
            """elements => elements.map(e => ({text: (e.innerText || '').trim(), href: e.href})).filter(x => x.href)""",
        )
        for item in hrefs:
            text = clean_text(item.get("text", "")).lower()
            if text in {"next", "next page", "next >", ">"}:
                return item.get("href", "")
        return ""

    def _parse_role_page(self, browser, url: str) -> Optional[JobPosting]:
        page = browser.new_page()
        page.set_default_timeout(45000)
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            title = self._extract_title(page)
            location = self._extract_location(page)
            description = self._extract_description(page)
            work_mode = self._extract_work_mode(page, description, location)
            apply_url = self._extract_apply_url(page, url)
            sponsorship_text = self._extract_sponsorship_text(description)
            job_id = self._extract_job_id(url, description)
            return JobPosting(
                title=title or "Unknown Title",
                description=description,
                location=location,
                work_mode=work_mode,
                company=self.company_name,
                sponsorship_text=sponsorship_text,
                apply_url=apply_url,
                job_id=job_id,
                source_url=url,
                metadata={"source": "walmart_collector"},
            )
        finally:
            page.close()

    def _extract_next_data(self, page) -> Dict[str, Any]:
        raw = page.eval_on_selector("script#__NEXT_DATA__", "el => el ? el.textContent : ''")
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
        return {}

    def _extract_title(self, page) -> str:
        selectors = [
            "h1",
            "[data-automation-id='jobPostingHeader']",
            "[data-automation-id='jobTitle']",
            "[data-testid='job-title']",
        ]
        for selector in selectors:
            locator = page.locator(selector).first
            if locator.count() > 0:
                text = clean_text(locator.inner_text())
                if text:
                    return text

        next_data = self._extract_next_data(page)
        possible = self._find_in_nested(next_data, ["title", "jobTitle", "name"])
        if possible:
            return clean_text(str(possible[0]))

        return "Unknown Title"

    def _extract_location(self, page) -> str:
        selectors = [
            "[data-automation-id='locations']",
            "[data-automation-id='primaryLocation']",
            "[data-automation-id='jobPostingHeader']",
            "[data-testid='job-location']",
        ]
        for selector in selectors:
            locator = page.locator(selector).first
            if locator.count() > 0:
                text = clean_text(locator.inner_text())
                if text and len(text) < 250:
                    return text

        next_data = self._extract_next_data(page)
        possible = self._find_in_nested(next_data, ["location", "locations", "jobLocation"])
        if possible:
            text = clean_text(str(possible[0]))
            if text:
                return text

        body = clean_text(page.locator("body").inner_text())
        m = re.search(r"locations?:\s*(.+?)(?:\s{2,}|posted on|time type|job requisition)", body, flags=re.IGNORECASE)
        return clean_text(m.group(1)) if m else ""

    def _extract_description(self, page) -> str:
        selectors = [
            "[data-automation-id='jobPostingDescription']",
            "[data-automation-id='jobDescription']",
            "[data-testid='job-description']",
            "main",
            "body",
        ]
        for selector in selectors:
            locator = page.locator(selector).first
            if locator.count() > 0:
                text = clean_text(locator.inner_text())
                if len(text) > 300:
                    return text

        next_data = self._extract_next_data(page)
        possible = self._find_in_nested(next_data, ["description", "jobDescription"])
        if possible:
            text = clean_text(str(possible[0]))
            if len(text) > 100:
                return text

        return clean_text(page.locator("body").inner_text())

    def _extract_work_mode(self, page, description: str, location: str) -> str:
        body = clean_text(page.locator("body").inner_text())
        combined = f"{body} {description} {location}".lower()
        if "remote" in combined:
            return "Remote"
        if "hybrid" in combined:
            return "Hybrid"
        if "onsite" in combined or "on-site" in combined or "in office" in combined:
            return "Onsite"
        return ""

    def _extract_apply_url(self, page, url: str) -> str:
        hrefs = page.eval_on_selector_all(
            "a",
            """elements => elements.map(e => ({text: (e.innerText || '').trim(), href: e.href})).filter(x => x.href)""",
        )
        for item in hrefs:
            text = clean_text(item.get("text", "")).lower()
            href = item.get("href", "")
            if any(token in text for token in ["apply", "apply now", "submit application", "start application"]):
                return href
        return url

    def _extract_job_id(self, url: str, description: str) -> str:
        m = WORKDAY_JOB_RE.search(url)
        if m:
            return m.group(1)
        m = CAREERS_JOB_RE.search(url)
        if m:
            return m.group(1)
        m = re.search(r"job requisition\s*[:#]?\s*([a-z]-?\d+)", description, flags=re.IGNORECASE)
        if m:
            return clean_text(m.group(1))
        return ""

    def _extract_sponsorship_text(self, description: str) -> str:
        matches: List[str] = []
        for pattern in [
            r"visa sponsorship[^.]*\.",
            r"sponsorship[^.]*\.",
            r"work authorization[^.]*\.",
            r"immigration[^.]*\.",
            r"not eligible for sponsorship[^.]*\.",
        ]:
            for m in re.findall(pattern, description, flags=re.IGNORECASE):
                matches.append(clean_text(m))
        return " ".join(uniq_preserve_order(matches))

    def _find_in_nested(self, data: Any, keys: List[str]) -> List[str]:
        results: List[str] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for k, v in value.items():
                    if any(key.lower() == str(k).lower() for key in keys):
                        if isinstance(v, (str, int, float)):
                            results.append(str(v))
                    walk(v)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(data)
        return uniq_preserve_order([clean_text(r) for r in results if clean_text(r)])


def collect_walmart_jobs(results_url: str = "https://walmart.wd5.myworkdayjobs.com/WalmartExternal", max_pages: int = 1, max_jobs: int = 20, headless: bool = True, company_name: str = "Walmart") -> List[JobPosting]:
    return WalmartCollector(results_url=results_url, max_pages=max_pages, max_jobs=max_jobs, headless=headless, company_name=company_name).collect()
