"""Plain-Python constraint checks for the Apply Agent — no framework/AI imports, no model calls
(docs/02-ARCHITECTURE.md §7.1: validation nodes are boolean comparisons against structured
fields already in Postgres, never routed through an LLM)."""

from dataclasses import dataclass, field

from src.domain.agent.entities import AgentConfig
from src.domain.job.entities import Job
from src.domain.job.entities import WorkMode as JobWorkMode
from src.domain.matching.entities import MatchScore


@dataclass
class ConstraintResult:
    passed: bool
    failures: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {"passed": self.passed, "failures": self.failures}


def check_min_score(match_score: MatchScore, min_match_score: int) -> str | None:
    if match_score.overall_score < min_match_score:
        return (
            f"Match score {round(match_score.overall_score)}% is below your minimum of "
            f"{min_match_score}%"
        )
    return None


def check_role_keywords(target_roles: list[str], job_title: str) -> str | None:
    roles = [role.strip().lower() for role in target_roles if role.strip()]
    if not roles:
        return None  # no preference configured — nothing to filter on
    title = job_title.lower()
    if any(role in title for role in roles):
        return None
    return f"Job title '{job_title}' doesn't match any of your target roles"


def check_skills(target_skills: list[str], job: Job) -> str | None:
    skills = {s.strip().lower() for s in target_skills if s.strip()}
    if not skills:
        return None
    job_skills = {
        s.strip().lower() for s in (*job.required_skills, *job.nice_to_have_skills) if s.strip()
    }
    if skills & job_skills:
        return None
    return "None of your target skills appear in this job's required or nice-to-have skills"


def check_work_mode(work_modes: list[JobWorkMode], job: Job) -> str | None:
    if not work_modes:
        return None
    if job.work_mode is None or job.work_mode in work_modes:
        return None
    return f"Job work mode '{job.work_mode.value}' isn't one of your accepted work modes"


def check_locations(target_locations: list[str], job: Job) -> str | None:
    locations = [loc.strip().lower() for loc in target_locations if loc.strip()]
    if not locations:
        return None
    if job.work_mode == JobWorkMode.REMOTE:
        return None  # location doesn't matter for a remote role
    job_location_parts = [
        part.lower()
        for part in (job.location.country, job.location.region, job.location.city)
        if part
    ]
    if not job_location_parts:
        return None  # job didn't disclose a location — don't penalize
    if any(loc in part for loc in locations for part in job_location_parts):
        return None
    return "Job location doesn't match any of your target locations"


def check_salary(min_salary: int | None, job: Job) -> str | None:
    if min_salary is None:
        return None
    job_ceiling = job.salary_max if job.salary_max is not None else job.salary_min
    if job_ceiling is None:
        return None  # job didn't disclose a range — don't penalize
    if job_ceiling >= min_salary:
        return None
    return f"Job's top salary ({job_ceiling}) is below your minimum of {min_salary}"


def evaluate_constraints(
    config: AgentConfig, job: Job, match_score: MatchScore
) -> ConstraintResult:
    failures = [
        failure
        for failure in (
            check_min_score(match_score, config.min_match_score),
            check_role_keywords(config.target_roles, job.title),
            check_skills(config.target_skills, job),
            check_work_mode(config.work_modes, job),
            check_locations(config.target_locations, job),
            check_salary(config.min_salary, job),
        )
        if failure is not None
    ]
    return ConstraintResult(passed=not failures, failures=failures)
