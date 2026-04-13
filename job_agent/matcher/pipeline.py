from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from .models import JobPosting, PipelineOutput, RankedJob
from .scorer import evaluate_job


class JobSearchPipeline:
    def __init__(
        self,
        exploratory_ratio: float = 0.30,
        max_per_company: Optional[int] = None,
        deduplicate_similar_titles: bool = True,
    ) -> None:
        self.exploratory_ratio = exploratory_ratio
        self.max_per_company = max_per_company
        self.deduplicate_similar_titles = deduplicate_similar_titles

    def run(self, jobs: List[JobPosting]) -> PipelineOutput:
        ranked_jobs: List[RankedJob] = []
        for job in jobs:
            match = evaluate_job(job)
            rank_score = self._compute_rank_score(job, match)
            bucket = self._assign_bucket(match)
            ranked_jobs.append(RankedJob(job=job, match=match, rank_score=rank_score, bucket=bucket))

        if self.deduplicate_similar_titles:
            ranked_jobs = self._deduplicate_jobs(ranked_jobs)
        ranked_jobs = self._limit_per_company(ranked_jobs)

        apply_now = sorted([r for r in ranked_jobs if r.bucket == "apply_now"], key=lambda x: x.rank_score, reverse=True)
        manual_review = sorted([r for r in ranked_jobs if r.bucket == "manual_review"], key=lambda x: x.rank_score, reverse=True)
        skip = sorted([r for r in ranked_jobs if r.bucket == "skip"], key=lambda x: x.rank_score, reverse=True)

        apply_now = self._rebalance_exploration(apply_now)

        return PipelineOutput(
            apply_now=apply_now,
            manual_review=manual_review,
            skip=skip,
            summary={
                "total_jobs_seen": len(jobs),
                "apply_now": len(apply_now),
                "manual_review": len(manual_review),
                "skip": len(skip),
            },
        )

    def _assign_bucket(self, match) -> str:
        if match.hard_skip or match.level == "skip":
            return "skip"
        if match.should_apply and match.level in {"strong", "moderate"}:
            return "apply_now"
        return "manual_review"

    def _compute_rank_score(self, job: JobPosting, match) -> float:
        score = float(match.score)
        title_text = f"{job.title} {job.description}".lower()
        if "backend" in title_text:
            score += 5
        if "platform" in title_text:
            score += 4
        if "distributed systems" in title_text or "distributed" in title_text:
            score += 4
        if "cloud" in title_text:
            score += 3
        if "full stack" in title_text:
            score += 1
        if "automation" in title_text or "tooling" in title_text:
            score += 2
        location_blob = f"{job.location} {job.work_mode} {job.description}".lower()
        if "remote" in location_blob:
            score += 3
        elif "hybrid" in location_blob:
            score += 2
        elif "onsite" in location_blob or "on site" in location_blob:
            score += 0.5
        if "staff" in title_text:
            score -= 1.5
        if "principal" in title_text:
            score -= 2.5
        score += min(len(match.matched_technologies) * 0.5, 3.0)
        return round(score, 2)

    def _deduplicate_jobs(self, ranked_jobs: List[RankedJob]) -> List[RankedJob]:
        best_by_key: Dict[str, RankedJob] = {}
        for ranked in ranked_jobs:
            normalized_title = self._normalize_title(ranked.job.title)
            source_hint = ranked.job.job_id or ranked.job.apply_url or ranked.job.source_url
            key = f"{ranked.job.company.lower()}::{normalized_title}::{source_hint}"
            current = best_by_key.get(key)
            if current is None or ranked.rank_score > current.rank_score:
                best_by_key[key] = ranked
        return list(best_by_key.values())

    def _normalize_title(self, title: str) -> str:
        title = title.lower()
        replacements = {"sr.": "senior", "sde": "software engineer", "swe": "software engineer", "developer": "software engineer"}
        for src, dst in replacements.items():
            title = title.replace(src, dst)
        return " ".join(title.split())

    def _limit_per_company(self, ranked_jobs: List[RankedJob]) -> List[RankedJob]:
        if self.max_per_company is None:
            return ranked_jobs
        grouped = defaultdict(list)
        for ranked in ranked_jobs:
            grouped[ranked.job.company.lower()].append(ranked)
        final_jobs = []
        for _, jobs in grouped.items():
            jobs_sorted = sorted(jobs, key=lambda x: x.rank_score, reverse=True)
            final_jobs.extend(jobs_sorted[: self.max_per_company])
        return final_jobs

    def _rebalance_exploration(self, apply_now: List[RankedJob]) -> List[RankedJob]:
        if not apply_now:
            return apply_now
        close_match, exploratory = [], []
        for ranked in apply_now:
            title_blob = f"{ranked.job.title} {ranked.job.description}".lower()
            is_top_family = any(
                phrase in title_blob
                for phrase in [
                    "senior software engineer",
                    "backend engineer",
                    "platform engineer",
                    "distributed systems engineer",
                    "cloud engineer",
                    "software engineer",
                ]
            )
            if ranked.match.level == "strong" and is_top_family:
                close_match.append(ranked)
            else:
                exploratory.append(ranked)
        total = len(apply_now)
        desired_exploratory = int(round(total * self.exploratory_ratio))
        final_list = close_match[:] + exploratory[:desired_exploratory]
        remaining = [r for r in apply_now if r not in final_list]
        final_list.extend(remaining)
        return sorted(final_list, key=lambda x: x.rank_score, reverse=True)


def print_pipeline_output(output: PipelineOutput, top_n: int = 10) -> None:
    print("=" * 100)
    print("PIPELINE SUMMARY")
    print("=" * 100)
    for key, value in output.summary.items():
        print(f"{key}: {value}")

    for bucket_name, jobs in [("APPLY NOW", output.apply_now), ("MANUAL REVIEW", output.manual_review), ("SKIP", output.skip)]:
        print("\n" + "=" * 100)
        print(bucket_name)
        print("=" * 100)
        for idx, ranked in enumerate(jobs[:top_n], start=1):
            print(f"{idx}. {ranked.job.company} | {ranked.job.title}")
            print(f"   Rank Score: {ranked.rank_score}")
            print(f"   Match Score: {ranked.match.score}")
            print(f"   Level: {ranked.match.level}")
            print(f"   Should Apply: {ranked.match.should_apply}")
            print(f"   Location: {ranked.job.location}")
            print(f"   Work Mode: {ranked.job.work_mode}")
            if ranked.job.job_id:
                print(f"   Job ID: {ranked.job.job_id}")
            if ranked.job.apply_url:
                print(f"   Apply URL: {ranked.job.apply_url}")
            if ranked.match.matched_experience_band:
                print(f"   Experience Match: {ranked.match.matched_experience_band}")
            if ranked.match.matched_technologies:
                print(f"   Technologies: {', '.join(ranked.match.matched_technologies)}")
            print("   Reasons:")
            for reason in ranked.match.reasons[:6]:
                print(f"    - {reason}")
            print()
