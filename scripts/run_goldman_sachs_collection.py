from __future__ import annotations

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from job_agent.collectors.goldman_sachs import GoldmanSachsCollector
from job_agent.matcher.pipeline import JobSearchPipeline, print_pipeline_output


def main() -> None:
    default_url = "https://higher.gs.com/results?&page=1&sort=RELEVANCE"

    raw_url = input(f"Enter Goldman Sachs results URL [{default_url}]: ").strip()
    url = raw_url or default_url

    raw_pages = input("Max result pages to scan [1]: ").strip()
    max_pages = int(raw_pages) if raw_pages else 1

    raw_jobs = input("Max jobs to parse [10]: ").strip()
    max_jobs = int(raw_jobs) if raw_jobs else 10

    print("\nCollecting Goldman Sachs jobs...")
    collector = GoldmanSachsCollector(
        results_url=url,
        max_pages=max_pages,
        max_jobs=max_jobs,
        headless=False,
    )
    jobs = collector.collect()

    print(f"\nCollected {len(jobs)} jobs. Running matcher...\n")

    pipeline = JobSearchPipeline(
        exploratory_ratio=0.30,
        max_per_company=10,
        deduplicate_similar_titles=True,
    )
    output = pipeline.run(jobs)
    print_pipeline_output(output, top_n=20)


if __name__ == "__main__":
    main()