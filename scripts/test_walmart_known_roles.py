from __future__ import annotations

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from job_agent.matcher.models import JobPosting
from job_agent.matcher.pipeline import JobSearchPipeline, print_pipeline_output


if __name__ == "__main__":
    jobs = [
        JobPosting(
            title="Software Engineer III",
            company="Walmart",
            location="Sunnyvale, CA, United States",
            work_mode="Hybrid",
            description="""
            You'll contribute to implementing robust technical solutions and tools for Walmart Technology organizations.
            Build backend services, APIs, and automation workflows. 5+ years of experience with Java, Python,
            distributed systems, cloud platforms, Kubernetes, CI/CD, and platform tooling.
            """,
        ),
        JobPosting(
            title="Senior, Software Engineer",
            company="Walmart",
            location="Bentonville, AR, United States",
            work_mode="Hybrid",
            description="""
            Lead scalable software solutions across backend services and internal developer platforms.
            Requires 6+ years using Java, Spring Boot, REST APIs, microservices, cloud, and distributed systems.
            """,
        ),
        JobPosting(
            title="Principal, Software Engineer",
            company="Walmart",
            location="Seattle, WA, United States",
            work_mode="Hybrid",
            description="""
            Design enterprise scale automation and AI-driven engineering workflows used across thousands of engineers.
            Requires 10+ years of experience. Strong Java, Python, cloud, APIs, Kubernetes, and platform architecture.
            """,
        ),
        JobPosting(
            title="Senior Frontend Engineer",
            company="Walmart",
            location="Remote, United States",
            work_mode="Remote",
            description="""
            Build React user interfaces, animation, and design systems. 5+ years frontend-heavy role.
            """,
        ),
    ]
    output = JobSearchPipeline(exploratory_ratio=0.30, max_per_company=20, deduplicate_similar_titles=True).run(jobs)
    print_pipeline_output(output, top_n=20)
