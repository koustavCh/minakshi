from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright
from job_agent.collectors.goldman_sachs import GoldmanSachsCollector

URL = "https://higher.gs.com/roles/166054"

collector = GoldmanSachsCollector(
    results_url="https://higher.gs.com/results?&page=1&sort=RELEVANCE",
    max_pages=1,
    max_jobs=1,
    headless=False,
)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    job = collector._parse_role_page(browser, URL)
    browser.close()

print("=" * 80)
print("TITLE:", repr(job.title))
print("LOCATION:", repr(job.location))
print("COMPANY:", repr(job.company))
print("SPONSORSHIP_TEXT:", repr(job.sponsorship_text))
print("DESCRIPTION PREVIEW:")
print(job.description[:1500])
print("=" * 80)
