from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class JobPosting:
    title: str
    description: str
    location: str = ""
    work_mode: str = ""
    company: str = ""
    sponsorship_text: str = ""
    apply_url: str = ""
    job_id: str = ""
    source_url: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class MatchResult:
    score: int
    level: str
    should_apply: bool
    hard_skip: bool
    reasons: List[str] = field(default_factory=list)
    matched_titles: List[str] = field(default_factory=list)
    matched_technologies: List[str] = field(default_factory=list)
    matched_experience_band: str = ""


@dataclass
class RankedJob:
    job: JobPosting
    match: MatchResult
    rank_score: float
    bucket: str


@dataclass
class PipelineOutput:
    apply_now: List[RankedJob] = field(default_factory=list)
    manual_review: List[RankedJob] = field(default_factory=list)
    skip: List[RankedJob] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
