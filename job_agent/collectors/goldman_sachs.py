from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set
import re

from job_agent.matcher.models import JobPosting


ROLE_LINK_RE = re.compile(r"https://higher\.gs\.com/roles/\d+")
WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def uniq_preserve_order(items: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


@dataclass
class GoldmanSachsCollector:
    results_url: str
    max_pages: int = 1
    max_jobs: int = 10
    headless: bool = False

    def collect(self) -> List[JobPosting]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.set_default_timeout(30000)

            role_links = self._collect_role_links(page)
            jobs: List[JobPosting] = []
            for link in role_links[: self.max_jobs]:
                job = self._parse_role_page(browser, link)
                if job:
                    jobs.append(job)
            browser.close()
            return jobs

    def _collect_role_links(self, page) -> List[str]:
        collected: List[str] = []
        current_url = self.results_url
        for _ in range(self.max_pages):
            page.goto(current_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            for _ in range(6):
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(1200)
            hrefs = page.eval_on_selector_all("a", """elements => elements.map(e => e.href).filter(Boolean)""")
            role_links = [href for href in hrefs if ROLE_LINK_RE.match(href)]
            collected.extend(role_links)
            collected = uniq_preserve_order(collected)
            next_url = self._find_next_page_url(page)
            if not next_url or next_url == current_url:
                break
            current_url = next_url
        return collected

    def _find_next_page_url(self, page) -> Optional[str]:
        hrefs = page.eval_on_selector_all("a", """elements => elements.map(e => ({text: (e.innerText || '').trim(), href: e.href}))""")
        for item in hrefs:
            text = clean_text(item.get("text", "")).lower()
            href = item.get("href", "")
            if text in {"next", "next page", ">"} and href:
                return href
        return None

    def _parse_role_page(self, browser, url: str) -> Optional[JobPosting]:
        page = browser.new_page()
        page.set_default_timeout(30000)
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            title = self._extract_title(page)
            location = self._extract_location(page)
            description = self._extract_description(page)
            apply_url = self._extract_apply_url(page)
            sponsorship_text = self._extract_sponsorship_text(description)
            job_id_match = re.search(r"/roles/(\d+)", url)
            return JobPosting(
                title=title or "Unknown Title",
                description=description,
                location=location,
                work_mode="",
                company="Goldman Sachs",
                sponsorship_text=sponsorship_text or "",
                apply_url=apply_url,
                job_id=job_id_match.group(1) if job_id_match else "",
                source_url=url,
            )
        finally:
            page.close()

    def _extract_title(self, page) -> str:
        selectors = ["h1", "[data-qa='job-title']", ".job-title"]
        for selector in selectors:
            locator = page.locator(selector).first
            if locator.count() > 0:
                text = clean_text(locator.inner_text())
                if text:
                    return text
        body_text = clean_text(page.locator("body").inner_text())
        m = re.search(r"(Engineering.*?|Software Engineering.*?|.*?Engineer.*?)\s+location_on\s+", body_text, flags=re.IGNORECASE)
        if m:
            candidate = clean_text(m.group(1))
            for marker in ["Engineering-", "Software Engineering", "Software Engineer", "Full Stack", "Backend", "Developer"]:
                idx = candidate.find(marker)
                if idx != -1:
                    candidate = candidate[idx:]
                    break
            return candidate
        m = re.search(r"^(.+?)\s+Apply", body_text, flags=re.IGNORECASE)
        if m:
            candidate = clean_text(m.group(1))
            if len(candidate) < 200:
                return candidate
        return "Unknown Title"

    def _extract_location(self, page) -> str:
        body_text = clean_text(page.locator("body").inner_text())
        m = re.search(r"location_on\s+(.+?)\s+share", body_text, flags=re.IGNORECASE)
        if m:
            return clean_text(m.group(1))
        for pattern in [r"Location\s*[:\-]\s*([^\n]+)", r"Location\s+([A-Z][A-Za-z\s,]+)"]:
            m = re.search(pattern, body_text, flags=re.IGNORECASE)
            if m:
                return clean_text(m.group(1))
        for selector in ["[data-qa='job-location']", ".job-location"]:
            locator = page.locator(selector).first
            if locator.count() > 0:
                text = clean_text(locator.inner_text())
                if text:
                    return text
        return ""

    def _extract_description(self, page) -> str:
        for selector in ["main", "[role='main']", ".content", "body"]:
            locator = page.locator(selector).first
            if locator.count() > 0:
                text = clean_text(locator.inner_text())
                if len(text) > 200:
                    return text
        return clean_text(page.locator("body").inner_text())

    def _extract_apply_url(self, page) -> str:
        hrefs = page.eval_on_selector_all("a", """elements => elements.map(e => ({text: (e.innerText || '').trim(), href: e.href})).filter(x => x.href)""")
        for item in hrefs:
            text = clean_text(item.get("text", "")).lower()
            href = item.get("href", "")
            if "apply" in text and href:
                return href
        return ""

    def _extract_sponsorship_text(self, description: str) -> str:
        matches = []
        for pattern in [r"visa sponsorship[^.]*\.", r"sponsorship[^.]*\.", r"work authorization[^.]*\.", r"immigration[^.]*\."]:
            for m in re.findall(pattern, description, flags=re.IGNORECASE):
                matches.append(clean_text(m))
        return " ".join(uniq_preserve_order(matches))


def collect_goldman_sachs_jobs(results_url: str, max_pages: int = 1, max_jobs: int = 10, headless: bool = False) -> List[JobPosting]:
    return GoldmanSachsCollector(results_url=results_url, max_pages=max_pages, max_jobs=max_jobs, headless=headless).collect()
