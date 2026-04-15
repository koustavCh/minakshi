from __future__ import annotations

"""
Guided Playwright application helper.

Behavior:
- opens apply URL
- attempts conservative auto-fill using known applicant profile fields
- asks the user for clarification when a mapped field has no profile value
- never clicks submit by default
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from job_agent.application.profile import ApplicantProfile


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


FIELD_ALIASES: Dict[str, List[str]] = {
    "full_name": ["full name", "name", "candidate name"],
    "email": ["email", "e-mail"],
    "phone": ["phone", "mobile", "phone number", "contact number"],
    "linkedin": ["linkedin"],
    "github": ["github"],
    "location": ["location", "city", "address"],
    "current_company": ["current company", "employer"],
    "current_title": ["current title", "job title", "designation"],
    "years_experience": ["years of experience", "experience"],
}


@dataclass
class FillStats:
    attempted: int = 0
    filled: int = 0
    skipped: int = 0


def needs_human_attention(page_text: str) -> bool:
    page_text = page_text.lower()
    return any(hint in page_text for hint in CRITICAL_QUESTION_HINTS)


def _selector_descriptor(item: Dict[str, str]) -> str:
    return " ".join(
        [
            item.get("label", ""),
            item.get("ariaLabel", ""),
            item.get("placeholder", ""),
            item.get("name", ""),
            item.get("id", ""),
        ]
    ).strip().lower()


def _profile_key_for_field(item: Dict[str, str]) -> Optional[str]:
    descriptor = _selector_descriptor(item)
    if not descriptor:
        return None
    for profile_key, aliases in FIELD_ALIASES.items():
        if any(alias in descriptor for alias in aliases):
            return profile_key
    return None


def _ask_missing_value(profile_key: str) -> str:
    return input(f"Missing profile value for '{profile_key}'. Please enter value (or leave blank to skip): ").strip()


def _ask_yes_no(prompt: str) -> bool:
    answer = input(f"{prompt} [y/n]: ").strip().lower()
    return answer in {"y", "yes"}


def _attempt_fill_inputs(page, profile: ApplicantProfile) -> FillStats:
    stats = FillStats()
    values = profile.to_fill_values()

    fields = page.eval_on_selector_all(
        "input, textarea",
        """elements => elements
            .filter(e => !e.disabled && e.type !== 'hidden')
            .map(e => ({
                name: e.getAttribute('name') || '',
                id: e.getAttribute('id') || '',
                type: (e.getAttribute('type') || '').toLowerCase(),
                placeholder: e.getAttribute('placeholder') || '',
                ariaLabel: e.getAttribute('aria-label') || '',
                label: (e.labels && e.labels.length ? e.labels[0].innerText : ''),
            }))""",
    )

    for item in fields:
        stats.attempted += 1
        profile_key = _profile_key_for_field(item)
        if not profile_key:
            stats.skipped += 1
            continue

        value = values.get(profile_key, "").strip()
        if not value:
            value = _ask_missing_value(profile_key)
        if not value:
            stats.skipped += 1
            continue

        selector = ""
        if item.get("name"):
            selector = f"input[name='{item['name']}'], textarea[name='{item['name']}']"
        elif item.get("id"):
            selector = f"#{item['id']}"
        elif item.get("ariaLabel"):
            label = item["ariaLabel"].replace("'", "\\'")
            selector = f"input[aria-label='{label}'], textarea[aria-label='{label}']"

        if not selector:
            stats.skipped += 1
            continue

        locator = page.locator(selector).first
        if locator.count() == 0:
            stats.skipped += 1
            continue

        try:
            locator.fill(value)
            stats.filled += 1
        except Exception:
            stats.skipped += 1

    return stats


def _attempt_fill_selects(page, profile: ApplicantProfile) -> FillStats:
    stats = FillStats()
    boolean_answers = {
        "authorized to work": profile.authorized_to_work_us,
        "work authorization": profile.authorized_to_work_us,
        "require sponsorship": profile.visa_sponsorship_required,
        "visa sponsorship": profile.visa_sponsorship_required,
    }

    selects = page.eval_on_selector_all(
        "select",
        """elements => elements
            .filter(e => !e.disabled)
            .map(e => ({
                name: e.getAttribute('name') || '',
                id: e.getAttribute('id') || '',
                ariaLabel: e.getAttribute('aria-label') || '',
                label: (e.labels && e.labels.length ? e.labels[0].innerText : ''),
                options: Array.from(e.options).map(o => (o.textContent || '').trim()).filter(Boolean),
            }))""",
    )

    for item in selects:
        stats.attempted += 1
        descriptor = _selector_descriptor(item)
        matching_prompt = next((key for key in boolean_answers.keys() if key in descriptor), None)
        if not matching_prompt:
            stats.skipped += 1
            continue

        answer = boolean_answers.get(matching_prompt)
        if answer is None:
            answer = _ask_yes_no(f"Clarification needed for '{matching_prompt}'. Answer yes?")

        desired = "yes" if answer else "no"
        options = [o.lower() for o in item.get("options", [])]
        target_label = None
        for idx, option in enumerate(options):
            if desired in option:
                target_label = item["options"][idx]
                break

        if not target_label:
            stats.skipped += 1
            continue

        selector = ""
        if item.get("name"):
            selector = f"select[name='{item['name']}']"
        elif item.get("id"):
            selector = f"#{item['id']}"
        elif item.get("ariaLabel"):
            label = item["ariaLabel"].replace("'", "\\'")
            selector = f"select[aria-label='{label}']"

        if not selector:
            stats.skipped += 1
            continue

        locator = page.locator(selector).first
        if locator.count() == 0:
            stats.skipped += 1
            continue

        try:
            locator.select_option(label=target_label)
            stats.filled += 1
        except Exception:
            stats.skipped += 1

    return stats


def run_apply_session(url: str, profile: ApplicantProfile, allow_submit: bool = False, headless: bool = False) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        print(f"Opened apply page: {url}")
        print("Attempting conservative field fill using applicant profile...")

        input_stats = _attempt_fill_inputs(page, profile)
        select_stats = _attempt_fill_selects(page, profile)

        print(
            f"Input fields: attempted={input_stats.attempted}, filled={input_stats.filled}, skipped={input_stats.skipped}"
        )
        print(
            f"Select fields: attempted={select_stats.attempted}, filled={select_stats.filled}, skipped={select_stats.skipped}"
        )

        page_text = page.locator("body").inner_text(timeout=7000)
        if needs_human_attention(page_text):
            print("Critical question detected. Please review answers before moving ahead.")

        if allow_submit:
            print("Submit is enabled, but this helper still does not click submit automatically.")

        print("Stopping before submit by design. Please review form manually in browser.")
        input("Press Enter to close browser...")
        browser.close()
