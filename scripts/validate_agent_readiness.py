from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_cmd(cmd: list[str]) -> bool:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode == 0


def run_live_check(company: str, url: str, years: int, max_pages: int, max_jobs: int) -> bool:
    print("\n[Live Gate] Running live collector + rank check...")
    try:
        from job_agent.agent import CompanyJobAgent, ResumeProfile
    except Exception as exc:  # pragma: no cover
        print(f"Live gate failed to import job agent: {exc}")
        return False

    try:
        agent = CompanyJobAgent()
        matches, output = agent.collect_and_rank(
            company_name=company,
            careers_url=url,
            resume_profile=ResumeProfile(years_experience=years),
            max_pages=max_pages,
            max_jobs=max_jobs,
            headless=True,
        )
    except Exception as exc:
        print(f"Live gate failed: {exc}")
        return False

    print(f"Collected jobs: {output.summary.get('total_jobs_seen', 0)}")
    print(f"Policy eligible: {len(output.apply_now) + len(output.manual_review)}")
    print(f"Experience qualified: {len(matches)}")

    return output.summary.get("total_jobs_seen", 0) > 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run readiness gates for Job Agent.")
    parser.add_argument("--live-company", default="", help="Company name for live gate, e.g. walmart")
    parser.add_argument("--live-url", default="", help="Live careers/results/job URL for runtime validation")
    parser.add_argument("--years", type=int, default=5, help="Resume years for live gate")
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--max-jobs", type=int, default=20)
    args = parser.parse_args()

    gates = []

    gates.append(("Unit smoke tests", run_cmd([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"])))
    gates.append((
        "Python compile checks",
        run_cmd(
            [
                sys.executable,
                "-m",
                "py_compile",
                "job_agent/agent.py",
                "job_agent/collectors/walmart.py",
                "job_agent/collectors/goldman_sachs.py",
                "job_agent/browser/playwright_apply.py",
                "scripts/run_company_collector.py",
                "tests/test_agent_smoke.py",
            ]
        ),
    ))

    if args.live_company and args.live_url:
        gates.append(
            (
                "Live collector gate",
                run_live_check(
                    company=args.live_company,
                    url=args.live_url,
                    years=args.years,
                    max_pages=args.max_pages,
                    max_jobs=args.max_jobs,
                ),
            )
        )
    else:
        print("\n[Live Gate] Skipped (provide --live-company and --live-url to run)")

    print("\n" + "=" * 80)
    print("READINESS RESULTS")
    print("=" * 80)
    all_ok = True
    for gate_name, ok in gates:
        status = "PASS" if ok else "FAIL"
        print(f"- {gate_name}: {status}")
        all_ok = all_ok and ok

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
