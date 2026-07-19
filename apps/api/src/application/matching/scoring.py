from src.domain.job.entities import WorkMode as JobWorkMode

MATCHER_VERSION = "v1"

_WEIGHT_SEMANTIC = 0.35
_WEIGHT_RERANK = 0.25
_WEIGHT_SKILL_OVERLAP = 0.15
_WEIGHT_EXPERIENCE_FIT = 0.10
_WEIGHT_SALARY_FIT = 0.10
_WEIGHT_LOCATION_FIT = 0.05


def semantic_score(cosine_similarity: float) -> float:
    return max(0.0, min(1.0, cosine_similarity)) * 100


def skill_overlap_score(candidate_skills: list[str], required_skills: list[str]) -> float:
    required_set = {s.strip().lower() for s in required_skills if s.strip()}
    if not required_set:
        return 100.0  # job didn't specify required skills — nothing to penalize against
    candidate_set = {s.strip().lower() for s in candidate_skills if s.strip()}
    overlap = candidate_set & required_set
    return (len(overlap) / len(required_set)) * 100


def experience_fit_score(candidate_years: float | None, min_years: float | None) -> float:
    if min_years is None or min_years <= 0:
        return 100.0  # job didn't specify a minimum
    if candidate_years is None:
        return 0.0  # job requires experience and candidate didn't disclose any
    if candidate_years >= min_years:
        return 100.0
    return max(0.0, (candidate_years / min_years) * 100)


def salary_fit_score(
    candidate_min: int | None,
    candidate_max: int | None,
    job_min: int | None,
    job_max: int | None,
) -> float:
    if candidate_min is None and candidate_max is None:
        return 100.0  # candidate didn't disclose an ask — don't penalize
    if job_min is None and job_max is None:
        return 100.0  # job didn't disclose a range

    c_lo = candidate_min if candidate_min is not None else 0
    c_hi = candidate_max if candidate_max is not None else c_lo
    j_lo = job_min if job_min is not None else 0
    j_hi = job_max if job_max is not None else j_lo

    if c_lo <= j_hi and j_lo <= c_hi:
        return 100.0  # ranges overlap

    gap = (c_lo - j_hi) if c_lo > j_hi else (j_lo - c_hi)
    reference = max(j_hi, c_lo, 1)
    return max(0.0, 100.0 - (gap / reference) * 100)


def matched_and_missing_skills(
    candidate_skills: list[str], required_skills: list[str]
) -> tuple[list[str], list[str]]:
    candidate_norm = {s.strip().lower() for s in candidate_skills if s.strip()}
    required = [s for s in required_skills if s.strip()]
    matched = sorted({s for s in required if s.strip().lower() in candidate_norm}, key=str.lower)
    missing = sorted(
        {s for s in required if s.strip().lower() not in candidate_norm}, key=str.lower
    )
    return matched, missing


def location_fit_score(
    job_work_mode: JobWorkMode | None,
    candidate_country: str | None,
    job_country: str | None,
) -> float:
    if job_work_mode == JobWorkMode.REMOTE:
        return 100.0  # location doesn't matter for a remote role
    if candidate_country is None or job_country is None:
        return 50.0  # unknown on one side — neutral, not full credit
    return 100.0 if candidate_country == job_country else 20.0


def compose_overall_score(
    *,
    semantic: float,
    rerank: float,
    skill_overlap: float,
    experience_fit: float,
    salary_fit: float,
    location_fit: float,
) -> float:
    return (
        _WEIGHT_SEMANTIC * semantic
        + _WEIGHT_RERANK * rerank
        + _WEIGHT_SKILL_OVERLAP * skill_overlap
        + _WEIGHT_EXPERIENCE_FIT * experience_fit
        + _WEIGHT_SALARY_FIT * salary_fit
        + _WEIGHT_LOCATION_FIT * location_fit
    )
