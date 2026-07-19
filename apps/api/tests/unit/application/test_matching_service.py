import uuid
from datetime import UTC, datetime

from src.application.ai.ports import RerankResult, VectorSearchResult
from src.domain.candidate.entities import Candidate, Resume, ResumeStatus
from src.domain.candidate.entities import Location as CandidateLocation
from src.domain.company.entities import Company
from src.domain.job.entities import Job, JobLifecycleStatus, JobProcessingStatus
from src.domain.job.entities import Location as JobLocation

from tests.unit.fakes import build_matching_service


def _make_candidate(**overrides: object) -> Candidate:
    now = datetime.now(UTC)
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        full_name="Jane Doe",
        headline="Backend Engineer",
        summary="Experienced backend engineer.",
        skills=["Python", "SQL"],
        total_experience_years=5.0,
        location=CandidateLocation(country="US"),
        desired_salary_min=100000,
        desired_salary_max=140000,
        work_mode_preference=None,
        work_experience=[],
        education=[],
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return Candidate(**defaults)  # type: ignore[arg-type]


def _make_job(**overrides: object) -> Job:
    now = datetime.now(UTC)
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        created_by_user_id=uuid.uuid4(),
        title="Backend Engineer",
        raw_description="We are hiring...",
        summary="Build and scale backend systems.",
        required_skills=["Python"],
        nice_to_have_skills=[],
        responsibilities=[],
        qualifications=[],
        min_experience_years=None,
        employment_type=None,
        work_mode=None,
        location=JobLocation(),
        salary_min=None,
        salary_max=None,
        lifecycle_status=JobLifecycleStatus.PUBLISHED,
        processing_status=JobProcessingStatus.READY,
        parser_version="v1",
        content_hash="job-hash-v1",
        error_message=None,
        version=1,
        published_at=now,
        closed_at=None,
        parsed_at=now,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return Job(**defaults)  # type: ignore[arg-type]


def _make_resume(candidate_id: uuid.UUID, **overrides: object) -> Resume:
    now = datetime.now(UTC)
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        version=1,
        s3_key="resumes/x.pdf",
        original_filename="resume.pdf",
        file_type="pdf",
        content_type="application/pdf",
        file_size=10,
        content_hash="cand-hash-v1",
        status=ResumeStatus.READY,
        parser_version="v1",
        error_message=None,
        uploaded_at=now,
        parsed_at=now,
    )
    defaults.update(overrides)
    return Resume(**defaults)  # type: ignore[arg-type]


def _make_company(**overrides: object) -> Company:
    now = datetime.now(UTC)
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        name="Acme",
        slug="acme",
        plan="free",
        usage_counters={},
        match_threshold=70,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return Company(**defaults)  # type: ignore[arg-type]


class TestComputeMatchesForJob:
    def test_noop_if_job_not_ready(self) -> None:
        harness = build_matching_service()
        job = _make_job(processing_status=JobProcessingStatus.PARSED)
        harness.jobs.add(job)

        harness.service.compute_matches_for_job(job.id)

        assert harness.match_scores.list_latest_for_job(job.id) == []

    def test_noop_if_job_has_no_vector(self) -> None:
        harness = build_matching_service()
        job = _make_job()
        harness.jobs.add(job)

        harness.service.compute_matches_for_job(job.id)

        assert harness.match_scores.list_latest_for_job(job.id) == []

    def test_computes_and_persists_score_for_matched_candidate(self) -> None:
        harness = build_matching_service()
        job = _make_job()
        harness.jobs.add(job)
        harness.vector_store.points.setdefault("jobs", {})[str(job.id)] = ([0.1] * 4, {})

        candidate = _make_candidate()
        harness.candidates.add(candidate)
        harness.resumes.add(_make_resume(candidate.id))

        harness.vector_store.search_results["candidates"] = [
            VectorSearchResult(point_id=str(candidate.id), score=0.9, payload={})
        ]

        harness.service.compute_matches_for_job(job.id)

        scores = harness.match_scores.list_latest_for_job(job.id)
        assert len(scores) == 1
        assert scores[0].candidate_id == candidate.id
        assert scores[0].semantic_score == 90.0
        assert scores[0].rerank_score == 50.0  # FakeRerankerClient default
        assert 0 < scores[0].overall_score <= 100

    def test_skips_candidate_missing_from_repository(self) -> None:
        harness = build_matching_service()
        job = _make_job()
        harness.jobs.add(job)
        harness.vector_store.points.setdefault("jobs", {})[str(job.id)] = ([0.1] * 4, {})
        harness.vector_store.search_results["candidates"] = [
            VectorSearchResult(point_id=str(uuid.uuid4()), score=0.9, payload={})
        ]

        harness.service.compute_matches_for_job(job.id)

        assert harness.match_scores.list_latest_for_job(job.id) == []

    def test_skips_recompute_when_content_hashes_unchanged(self) -> None:
        harness = build_matching_service()
        job = _make_job()
        harness.jobs.add(job)
        harness.vector_store.points.setdefault("jobs", {})[str(job.id)] = ([0.1] * 4, {})
        candidate = _make_candidate()
        harness.candidates.add(candidate)
        harness.resumes.add(_make_resume(candidate.id))
        harness.vector_store.search_results["candidates"] = [
            VectorSearchResult(point_id=str(candidate.id), score=0.9, payload={})
        ]

        harness.service.compute_matches_for_job(job.id)
        assert len(harness.match_scores.list_latest_for_job(job.id)) == 1
        assert len(harness.reranker.calls) == 1

        harness.service.compute_matches_for_job(job.id)
        assert len(harness.match_scores.list_latest_for_job(job.id)) == 1
        assert len(harness.reranker.calls) == 1  # not called again — nothing changed

    def test_recomputes_when_candidate_resume_hash_changes(self) -> None:
        harness = build_matching_service()
        job = _make_job()
        harness.jobs.add(job)
        harness.vector_store.points.setdefault("jobs", {})[str(job.id)] = ([0.1] * 4, {})
        candidate = _make_candidate()
        harness.candidates.add(candidate)
        harness.resumes.add(_make_resume(candidate.id, version=1, content_hash="cand-hash-v1"))
        harness.vector_store.search_results["candidates"] = [
            VectorSearchResult(point_id=str(candidate.id), score=0.9, payload={})
        ]

        harness.service.compute_matches_for_job(job.id)
        assert len(harness.reranker.calls) == 1

        # simulate a re-uploaded/re-embedded resume with different content
        harness.resumes.add(
            _make_resume(candidate.id, id=uuid.uuid4(), version=2, content_hash="cand-hash-v2")
        )

        harness.service.compute_matches_for_job(job.id)
        assert len(harness.reranker.calls) == 2  # recomputed since the candidate's content changed


class TestComputeMatchesForCandidate:
    def test_noop_if_candidate_missing(self) -> None:
        harness = build_matching_service()

        harness.service.compute_matches_for_candidate(uuid.uuid4())  # should not raise

    def test_only_matches_published_ready_jobs(self) -> None:
        harness = build_matching_service()
        candidate = _make_candidate()
        harness.candidates.add(candidate)
        harness.resumes.add(_make_resume(candidate.id))
        harness.vector_store.points.setdefault("candidates", {})[str(candidate.id)] = (
            [0.2] * 4,
            {},
        )

        draft_job = _make_job(lifecycle_status=JobLifecycleStatus.DRAFT)
        harness.jobs.add(draft_job)
        not_ready_job = _make_job(processing_status=JobProcessingStatus.PARSED)
        harness.jobs.add(not_ready_job)
        good_job = _make_job()
        harness.jobs.add(good_job)

        harness.vector_store.search_results["jobs"] = [
            VectorSearchResult(point_id=str(draft_job.id), score=0.9, payload={}),
            VectorSearchResult(point_id=str(not_ready_job.id), score=0.9, payload={}),
            VectorSearchResult(point_id=str(good_job.id), score=0.9, payload={}),
        ]

        harness.service.compute_matches_for_candidate(candidate.id)

        scores = harness.match_scores.list_latest_for_candidate(candidate.id)
        assert [s.job_id for s in scores] == [good_job.id]


class TestGetJobCandidates:
    def test_filters_by_threshold_and_orders_descending(self) -> None:
        harness = build_matching_service()
        job = _make_job()
        harness.jobs.add(job)
        candidate_low = _make_candidate()
        candidate_high = _make_candidate()
        harness.candidates.add(candidate_low)
        harness.candidates.add(candidate_high)
        harness.resumes.add(_make_resume(candidate_low.id))
        harness.resumes.add(_make_resume(candidate_high.id))

        harness.vector_store.points.setdefault("jobs", {})[str(job.id)] = ([0.1] * 4, {})
        harness.vector_store.search_results["candidates"] = [
            VectorSearchResult(point_id=str(candidate_low.id), score=0.3, payload={}),
            VectorSearchResult(point_id=str(candidate_high.id), score=0.95, payload={}),
        ]
        harness.reranker.results = [
            RerankResult(id=str(candidate_low.id), score=10.0),
            RerankResult(id=str(candidate_high.id), score=95.0),
        ]

        harness.service.compute_matches_for_job(job.id)

        results = harness.service.get_job_candidates(job.id, threshold=70)
        assert [r.candidate_id for r in results] == [candidate_high.id]


class TestGetRecommendedJobs:
    def test_excludes_closed_jobs_and_applies_company_threshold(self) -> None:
        harness = build_matching_service()
        candidate = _make_candidate()
        harness.candidates.add(candidate)
        harness.resumes.add(_make_resume(candidate.id))
        harness.vector_store.points.setdefault("candidates", {})[str(candidate.id)] = (
            [0.2] * 4,
            {},
        )

        strict_company = harness.companies.add(_make_company(match_threshold=90))
        lenient_company = harness.companies.add(_make_company(match_threshold=10))

        job_strict = _make_job(company_id=strict_company.id)
        job_lenient = _make_job(company_id=lenient_company.id)
        job_closed = _make_job(
            company_id=lenient_company.id, lifecycle_status=JobLifecycleStatus.CLOSED
        )
        harness.jobs.add(job_strict)
        harness.jobs.add(job_lenient)
        harness.jobs.add(job_closed)

        harness.vector_store.search_results["jobs"] = [
            VectorSearchResult(point_id=str(job_strict.id), score=0.5, payload={}),
            VectorSearchResult(point_id=str(job_lenient.id), score=0.5, payload={}),
            # job_closed is included in the search hits to prove it's filtered out even when a
            # (stale) Qdrant payload would otherwise have surfaced it — CLOSED jobs never get a
            # match_scores row written for them at all (avoids wasting rerank cost on them).
            VectorSearchResult(point_id=str(job_closed.id), score=0.5, payload={}),
        ]
        harness.reranker.results = None  # default 50.0 for every candidate

        harness.service.compute_matches_for_candidate(candidate.id)
        scored_job_ids = {
            s.job_id for s in harness.match_scores.list_latest_for_candidate(candidate.id)
        }
        assert job_closed.id not in scored_job_ids

        recommended = harness.service.get_recommended_jobs(candidate.id)
        assert [r.job_id for r in recommended] == [job_lenient.id]
