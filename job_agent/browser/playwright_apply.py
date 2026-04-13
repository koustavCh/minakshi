from __future__ import annotations

"""
Playwright automation scaffold.

This file is intentionally conservative:
- opens the page
- illustrates where to log in / create account
- illustrates where to fill fields
- pauses for critical questions
- does not press submit

To use for real sites, add company/ATS-specific selectors and flows.
"""

from playwright.sync_api import sync_playwright


CRITICAL_QUESTION_HINTS = [
    "sponsorship",
    "salary",
    "relocate",
    "relocation",
    "start date",
    "criminal",
    "clearance",
    "security",
    "export control",
    "authorized to work",
]


def needs_human_attention(page_text: str) -> bool:
    page_text = page_text.lower()
    return any(hint in page_text for hint in CRITICAL_QUESTION_HINTS)


def run_apply_session(url: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")

        print(f"Opened: {url}")
        print("Add site-specific login/account-creation steps here.")
        print("Add site-specific form-fill logic here.")

        page_text = page.locator("body").inner_text(timeout=5000)
        if needs_human_attention(page_text):
            print("Critical question detected. Review required before continuing.")
        else:
            print("No obvious critical question detected on current page.")

        print("Stopping before submit by design.")
        input("Press Enter to close browser...")
        browser.close()
