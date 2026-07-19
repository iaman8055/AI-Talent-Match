from src.application.matching.scoring import (
    compose_overall_score,
    experience_fit_score,
    location_fit_score,
    salary_fit_score,
    semantic_score,
    skill_overlap_score,
)
from src.domain.job.entities import WorkMode


class TestSemanticScore:
    def test_scales_to_0_100(self) -> None:
        assert semantic_score(1.0) == 100.0
        assert semantic_score(0.5) == 50.0
        assert semantic_score(0.0) == 0.0

    def test_clamps_out_of_range_values(self) -> None:
        assert semantic_score(1.5) == 100.0
        assert semantic_score(-0.5) == 0.0


class TestSkillOverlapScore:
    def test_full_overlap_scores_100(self) -> None:
        assert skill_overlap_score(["Python", "SQL"], ["python", "sql"]) == 100.0

    def test_partial_overlap_scores_proportionally(self) -> None:
        assert skill_overlap_score(["Python"], ["python", "sql"]) == 50.0

    def test_no_required_skills_scores_neutral_100(self) -> None:
        assert skill_overlap_score(["Python"], []) == 100.0

    def test_no_overlap_scores_0(self) -> None:
        assert skill_overlap_score(["Go"], ["python"]) == 0.0


class TestExperienceFitScore:
    def test_no_minimum_scores_100(self) -> None:
        assert experience_fit_score(1.0, None) == 100.0

    def test_meets_or_exceeds_minimum_scores_100(self) -> None:
        assert experience_fit_score(5.0, 5.0) == 100.0
        assert experience_fit_score(10.0, 5.0) == 100.0

    def test_below_minimum_scores_proportionally(self) -> None:
        assert experience_fit_score(2.5, 5.0) == 50.0

    def test_undisclosed_experience_against_a_requirement_scores_0(self) -> None:
        assert experience_fit_score(None, 5.0) == 0.0


class TestSalaryFitScore:
    def test_missing_data_on_either_side_scores_neutral_100(self) -> None:
        assert salary_fit_score(None, None, 100000, 150000) == 100.0
        assert salary_fit_score(100000, 150000, None, None) == 100.0

    def test_overlapping_ranges_score_100(self) -> None:
        assert salary_fit_score(100000, 140000, 120000, 160000) == 100.0

    def test_disjoint_ranges_score_below_100(self) -> None:
        score = salary_fit_score(200000, 220000, 100000, 150000)
        assert 0.0 <= score < 100.0


class TestLocationFitScore:
    def test_remote_job_scores_100_regardless_of_location(self) -> None:
        assert location_fit_score(WorkMode.REMOTE, "US", "IN") == 100.0

    def test_matching_country_scores_100(self) -> None:
        assert location_fit_score(WorkMode.ONSITE, "US", "US") == 100.0

    def test_mismatched_country_scores_low(self) -> None:
        assert location_fit_score(WorkMode.ONSITE, "US", "IN") == 20.0

    def test_missing_location_data_scores_neutral(self) -> None:
        assert location_fit_score(WorkMode.ONSITE, None, "US") == 50.0


class TestComposeOverallScore:
    def test_all_max_scores_yields_100(self) -> None:
        overall = compose_overall_score(
            semantic=100,
            rerank=100,
            skill_overlap=100,
            experience_fit=100,
            salary_fit=100,
            location_fit=100,
        )
        assert overall == 100.0

    def test_all_zero_scores_yields_0(self) -> None:
        overall = compose_overall_score(
            semantic=0, rerank=0, skill_overlap=0, experience_fit=0, salary_fit=0, location_fit=0
        )
        assert overall == 0.0

    def test_weights_semantic_and_rerank_most_heavily(self) -> None:
        semantic_heavy = compose_overall_score(
            semantic=100, rerank=0, skill_overlap=0, experience_fit=0, salary_fit=0, location_fit=0
        )
        location_heavy = compose_overall_score(
            semantic=0, rerank=0, skill_overlap=0, experience_fit=0, salary_fit=0, location_fit=100
        )
        assert semantic_heavy > location_heavy
