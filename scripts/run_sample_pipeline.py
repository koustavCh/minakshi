import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from job_agent.matcher.models import JobPosting
from job_agent.matcher.pipeline import JobSearchPipeline, print_pipeline_output


if __name__ == "__main__":
    jobs = [
        JobPosting(
            title="Senior Backend Engineer",
            company="ExampleCloud",
            location="United States",
            work_mode="Remote",
            sponsorship_text="H-1B sponsorship available for qualified candidates.",
            description="""
            We are hiring a Senior Backend Engineer with 5+ years of experience.
            Strong Java or Python required. Experience with REST APIs, microservices,
            distributed systems, Kubernetes, Terraform, and GCP preferred.
            """,
        ),
        JobPosting(
            title="Platform Engineer",
            company="InfraWorks",
            location="Austin, United States",
            work_mode="Hybrid",
            sponsorship_text="Visa sponsorship available.",
            description="""
            Looking for 6+ years of experience with cloud infrastructure, OCI or GCP,
            Terraform, Kubernetes, backend services, APIs, and distributed systems.
            """,
        ),
        JobPosting(
            title="Full Stack Engineer",
            company="AppFlow",
            location="United States",
            work_mode="Remote",
            sponsorship_text="Sponsorship available.",
            description="""
            5+ years building enterprise applications with React, Java, Python, REST APIs,
            microservices, and cloud deployment experience.
            """,
        ),
        JobPosting(
            title="Senior Frontend Engineer",
            company="UIWorks",
            location="Remote, United States",
            work_mode="Remote",
            sponsorship_text="Visa sponsorship available.",
            description="""
            5+ years of frontend-heavy React development, animation systems, and design systems.
            """,
        ),
        JobPosting(
            title="Staff Software Engineer",
            company="BigInfra",
            location="California, United States",
            work_mode="Hybrid",
            sponsorship_text="Visa sponsorship available.",
            description="""
            Looking for 10+ years of experience leading large distributed systems.
            Deep backend architecture, cloud infrastructure, Java, Python, Kubernetes,
            Terraform, and cross-team technical leadership required.
            """,
        ),
        JobPosting(
            title="Senior Software Engineer",
            company="NoSponsor Inc",
            location="United States",
            work_mode="Remote",
            sponsorship_text="This role is not eligible for sponsorship.",
            description="""
            Senior software engineer. 5+ years. Java, APIs, cloud systems.
            """,
        ),
    ]

    pipeline = JobSearchPipeline(exploratory_ratio=0.30, max_per_company=3, deduplicate_similar_titles=True)
    output = pipeline.run(jobs)
    print_pipeline_output(output)
