import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from job_agent.browser.playwright_apply import run_apply_session


if __name__ == "__main__":
    url = input("Enter a career page URL: ").strip()
    run_apply_session(url)
