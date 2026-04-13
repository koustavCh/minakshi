from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple
import re


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


POLICY = {
    "role_priority": {
        "senior software engineer": 1,
        "backend engineer": 2,
        "full stack engineer": 3,
        "staff software engineer": 4,
        "principal software engineer": 5,
        "platform engineer": 6,
        "product engineer": 7,
        "cloud engineer": 8,
        "distributed systems engineer": 9,
        "software developer": 10,
        "member of technical staff": 11,
        "application engineer": 12,
        "software engineer": 13,
        "software engineering": 14,
        "developer": 15,
        "engineer": 16,
    },
    "staff_principal_require_close_match": True,
    "roles_to_skip": [
        "frontend engineer",
        "front end engineer",
        "mobile engineer",
        "android engineer",
        "ios engineer",
        "devops engineer",
        "site reliability engineer",
        "ml scientist",
        "machine learning scientist",
        "qa engineer",
        "test engineer",
        "support engineer",
    ],
    "technology_terms": [
        "java",
        "python",
        "rest",
        "rest api",
        "rest apis",
        "apis",
        "distributed systems",
        "distributed system",
        "microservices",
        "microservice",
        "cloud",
        "oci",
        "gcp",
        "azure",
        "aws",
        "kubernetes",
        "terraform",
        "react",
        "spring",
        "spring boot",
        "springboot",
        "asynchronous messaging",
        "async messaging",
        "pub/sub",
        "pubsub",
        "rabbitmq",
        "kafka",
        "sql",
        "database",
        "graphql",
        "java 17",
        "distributed tracing",
        "ci/cd",
    ],
    "hard_skip_phrases": [
        "no sponsorship",
        "will not sponsor",
        "not eligible for sponsorship",
        "unable to sponsor",
        "clearance required",
        "security clearance required",
        "must be eligible for clearance",
    ],
    "sponsorship_positive_phrases": [
        "visa sponsorship available",
        "sponsorship available",
        "will sponsor",
        "h-1b sponsorship",
        "immigration support",
        "work authorization support",
        "candidates requiring sponsorship may be considered",
        "sponsorship may be available",
    ],
    "unclear_sponsorship_manual_review_companies": [
        "goldman sachs",
        "walmart",
        "walmart global tech",
        "sam's club",
    ],
    "goldman_title_labels": [
        "vice president",
        "associate",
        "analyst",
        "executive director",
    ],
    "thresholds": {
        "strong_match_min": 80,
        "moderate_match_min": 65,
    },
}


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9+/#\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def contains_phrase(text: str, phrases: List[str]) -> List[str]:
    normalized = normalize(text)
    return [p for p in phrases if p in normalized]


def extract_experience_years(text: str) -> Set[int]:
    normalized = normalize(text)
    matches = re.findall(r"(\d{1,2})\s*\+?\s*(?:years|year|yrs|yr)", normalized)
    return {int(m) for m in matches}


def match_experience_band(years_found: Set[int]) -> Tuple[str, int]:
    priority = [5, 6, 4, 8, 10]
    if not years_found:
        return "", 6
    for p in priority:
        if p in years_found:
            return f"{p}+", 15
    if any(y in years_found for y in [3, 7, 9]):
        return f"{sorted(years_found)[0]}+", 8
    return f"{sorted(years_found)[0]}+", 4


def company_key(company: str) -> str:
    return normalize(company)


def is_goldman_sachs(company: str) -> bool:
    c = company_key(company)
    return "goldman sachs" in c or c == "goldman"


def is_walmart(company: str) -> bool:
    c = company_key(company)
    return "walmart" in c or "sam s club" in c


def allows_unclear_sponsorship(company: str) -> bool:
    c = company_key(company)
    return any(name in c for name in POLICY["unclear_sponsorship_manual_review_companies"])


def title_score(job_title: str, description: str, company: str) -> Tuple[int, List[str], bool]:
    title_text = normalize(job_title)
    desc_text = normalize(description)
    combined = f"{title_text} {desc_text}"
    matched = []
    close_match_required = False
    goldman = is_goldman_sachs(company)

    for title, rank in POLICY["role_priority"].items():
        if title in combined:
            matched.append(title)

    if not matched:
        if goldman and any(term in desc_text for term in ["software engineering", "software engineer", "engineer", "developer"]):
            return 12, ["goldman engineering-description fallback"], False
        return 0, [], False

    best_rank = min(POLICY["role_priority"][t] for t in matched)
    rank_to_score_default = {1: 25,2: 23,3: 20,4: 18,5: 16,6: 21,7: 17,8: 19,9: 21,10: 16,11: 16,12: 14,13: 18,14: 18,15: 14,16: 12}
    rank_to_score_goldman = {1: 20,2: 19,3: 17,4: 16,5: 14,6: 18,7: 15,8: 17,9: 18,10: 14,11: 14,12: 12,13: 16,14: 16,15: 12,16: 10}
    score = (rank_to_score_goldman if goldman else rank_to_score_default).get(best_rank, 10)

    if "staff software engineer" in matched or "principal software engineer" in matched:
        close_match_required = True

    if goldman:
        label_hits = [lbl for lbl in POLICY["goldman_title_labels"] if lbl in title_text]
        if label_hits:
            matched.extend([f"gs-level:{x}" for x in label_hits])

    return score, sorted(set(matched)), close_match_required


def technology_score(description: str, company: str) -> Tuple[int, List[str]]:
    desc = normalize(description)
    matched = sorted(set(term for term in POLICY["technology_terms"] if term in desc))
    if not matched:
        return 0, []
    per_term = 4 if is_goldman_sachs(company) else 3
    raw = min(len(matched) * per_term, 30 if is_goldman_sachs(company) else 25)
    return raw, matched


def alignment_score(description: str, company: str) -> Tuple[int, List[str]]:
    desc = normalize(description)
    reasons: List[str] = []
    score = 0
    if any(x in desc for x in ["backend", "server side"]):
        score += 5
        reasons.append("backend-heavy scope")
    if any(x in desc for x in ["distributed systems", "distributed system", "distributed"]):
        score += 5
        reasons.append("distributed systems alignment")
    if any(x in desc for x in ["cloud", "oci", "gcp", "aws", "azure", "kubernetes", "terraform"]):
        score += 5
        reasons.append("cloud/infrastructure alignment")
    if any(x in desc for x in ["software engineering", "software engineer", "developer", "coding", "programming"]):
        score += 4
        reasons.append("clear software-engineering content")
    if any(x in desc for x in ["api", "apis", "rest", "microservices", "microservice", "graphql"]):
        score += 4
        reasons.append("api/service-development alignment")
    if any(x in desc for x in ["automation", "platform", "tooling", "reliability"]):
        score += 2
        reasons.append("platform/tooling alignment")
    cap = 22 if is_goldman_sachs(company) else 17
    return min(score, cap), reasons


def sponsorship_score(job: JobPosting) -> Tuple[int, bool, List[str]]:
    combined = normalize(" ".join([job.title, job.description, job.sponsorship_text]))
    hard_skip_hits = contains_phrase(combined, POLICY["hard_skip_phrases"])
    if hard_skip_hits:
        return 0, True, [f"hard skip phrase found: {hit}" for hit in hard_skip_hits]
    positive_hits = contains_phrase(combined, POLICY["sponsorship_positive_phrases"])
    if positive_hits:
        return 15, False, [f"sponsorship supported: {hit}" for hit in positive_hits]
    if allows_unclear_sponsorship(job.company):
        return 0, False, [f"sponsorship not explicitly stated on {job.company or 'company'} page"]
    return 0, True, ["sponsorship not explicitly supported"]


def work_mode_score(location: str, work_mode: str, description: str) -> Tuple[int, List[str]]:
    combined = normalize(f"{location} {work_mode} {description}")
    reasons: List[str] = []
    score = 0
    if "remote" in combined:
        score = 5
        reasons.append("remote-friendly")
    elif "hybrid" in combined:
        score = 4
        reasons.append("hybrid okay")
    elif "onsite" in combined or "on site" in combined:
        score = 2
        reasons.append("onsite okay")
    if any(x in combined for x in ["united states", "u s", "usa"]):
        reasons.append("u.s. location fit")
    return score, reasons


def role_skip_check(job_title: str, description: str) -> Tuple[bool, List[str]]:
    combined = normalize(f"{job_title} {description}")
    hits = [role for role in POLICY["roles_to_skip"] if role in combined]
    return (len(hits) > 0), [f"excluded role category: {h}" for h in hits]


def unusually_close_match(title_points: int, tech_points: int, alignment_points: int, exp_points: int) -> bool:
    return title_points >= 16 and tech_points >= 18 and alignment_points >= 10 and exp_points >= 8


def evaluate_job(job: JobPosting) -> MatchResult:
    reasons: List[str] = []
    goldman = is_goldman_sachs(job.company)
    walmart = is_walmart(job.company)

    skip_role, skip_reasons = role_skip_check(job.title, job.description)
    if skip_role:
        return MatchResult(score=0, level="skip", should_apply=False, hard_skip=True, reasons=skip_reasons)

    title_points, matched_titles, requires_close_match = title_score(job.title, job.description, job.company)
    reasons.append(f"title/role match: {', '.join(matched_titles)}" if matched_titles else "weak title match")

    years_found = extract_experience_years(f"{job.title} {job.description}")
    matched_experience_band, exp_points = match_experience_band(years_found)
    reasons.append(f"experience band match: {matched_experience_band}" if matched_experience_band else "experience band not explicitly stated")

    tech_points, matched_techs = technology_score(job.description, job.company)
    reasons.append(f"technology overlap: {', '.join(matched_techs)}" if matched_techs else "low technology overlap")

    align_points, align_reasons = alignment_score(job.description, job.company)
    reasons.extend(align_reasons if align_reasons else ["limited backend/cloud/distributed alignment"])

    sponsor_points, sponsor_hard_skip, sponsor_reasons = sponsorship_score(job)
    reasons.extend(sponsor_reasons)
    if sponsor_hard_skip:
        return MatchResult(score=0, level="skip", should_apply=False, hard_skip=True, reasons=reasons, matched_titles=matched_titles, matched_technologies=matched_techs, matched_experience_band=matched_experience_band)

    work_points, work_reasons = work_mode_score(job.location, job.work_mode, job.description)
    reasons.extend(work_reasons if work_reasons else ["work mode not clearly favorable"])

    total = title_points + exp_points + tech_points + align_points + sponsor_points + work_points

    if goldman and any(x in normalize(job.description) for x in ["software engineering", "software engineer", "developer", "java", "python", "react", "springboot", "spring boot"]):
        total += 8
        reasons.append("goldman-specific boost: engineering JD over business title")

    if walmart and any(x in normalize(job.description) for x in ["automation", "platform", "scalable", "backend", "services", "ai driven engineering workflows"]):
        total += 4
        reasons.append("walmart-specific boost: platform/automation/backend alignment")

    if requires_close_match and POLICY["staff_principal_require_close_match"] and not unusually_close_match(title_points, tech_points, align_points, exp_points):
        reasons.append("staff/principal role not unusually close to background")
        return MatchResult(score=total, level="manual_review", should_apply=False, hard_skip=False, reasons=reasons, matched_titles=matched_titles, matched_technologies=matched_techs, matched_experience_band=matched_experience_band)

    strong_min = POLICY["thresholds"]["strong_match_min"]
    moderate_min = POLICY["thresholds"]["moderate_match_min"]
    unclear_sponsorship = any("sponsorship not explicitly stated on" in reason for reason in reasons)

    if unclear_sponsorship:
        level = "manual_review"
        should_apply = False
    elif total >= strong_min:
        level = "strong"
        should_apply = True
    elif total >= moderate_min:
        level = "moderate"
        should_apply = True
    else:
        level = "manual_review"
        should_apply = False

    return MatchResult(
        score=total,
        level=level,
        should_apply=should_apply,
        hard_skip=False,
        reasons=reasons,
        matched_titles=matched_titles,
        matched_technologies=matched_techs,
        matched_experience_band=matched_experience_band,
    )
