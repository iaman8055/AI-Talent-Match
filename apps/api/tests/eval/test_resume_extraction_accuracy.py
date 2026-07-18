"""Golden-set eval for resume structured extraction accuracy.

Makes real calls to Ollama Cloud, so it's skipped unless OLLAMA_API_KEY is set and it's not part
of the default CI `pytest` run (see .github/workflows/ci.yml) — run manually with:

    uv run pytest tests/eval -q -s

Small on purpose per docs/03-ROADMAP.md Phase 2 ("starts here, grows over time"). Add more
(filename, expected) pairs to _GOLDEN_SET as the golden set grows.
"""

from pathlib import Path

import pytest
from src.application.candidate.extraction_schema import (
    RESUME_EXTRACTION_INSTRUCTIONS,
    ResumeExtractionResult,
)
from src.core.config import get_settings
from src.infrastructure.ai.ollama_client import OllamaClient

_GOLDEN_DIR = Path(__file__).parent / "golden_resumes"

_GOLDEN_SET = [
    (
        "001_backend_engineer.txt",
        {
            "full_name": "Alex Rivera",
            "expected_skills": {"python", "go", "postgresql", "redis", "kubernetes", "aws"},
        },
    ),
    (
        "002_data_scientist.txt",
        {
            "full_name": "Priya Natarajan",
            "expected_skills": {"python", "pytorch", "sql", "scikit-learn", "airflow", "docker"},
        },
    ),
    (
        "003_product_manager.txt",
        {
            "full_name": "Marcus Webb",
            "expected_skills": {"product strategy", "roadmapping", "sql", "a/b testing"},
        },
    ),
    (
        "004_entry_level.txt",
        {
            "full_name": "Sofia Chen",
            "expected_skills": {"javascript", "typescript", "react", "css", "git"},
        },
    ),
    (
        "005_marketing_manager.txt",
        {
            "full_name": "Daniela Ortiz",
            "expected_skills": {"seo", "hubspot", "content strategy", "google analytics"},
        },
    ),
]


def _skills_overlap(extracted: list[str], expected: set[str]) -> float:
    normalized = {s.strip().lower() for s in extracted}
    if not expected:
        return 1.0
    return len(normalized & expected) / len(expected)


@pytest.mark.skipif(
    not get_settings().ollama_api_key,
    reason="OLLAMA_API_KEY not set — eval harness needs a real key",
)
def test_resume_extraction_golden_set_accuracy() -> None:
    settings = get_settings()
    client = OllamaClient(
        base_url=settings.ollama_base_url,
        api_key=settings.ollama_api_key,
        llm_model=settings.ollama_llm_model,
        embedding_model=settings.ollama_embedding_model,
    )

    name_matches = 0
    skill_scores: list[float] = []
    per_resume_results: list[tuple[str, bool, float]] = []

    for filename, expected in _GOLDEN_SET:
        text = (_GOLDEN_DIR / filename).read_text()
        result = client.extract_structured(
            RESUME_EXTRACTION_INSTRUCTIONS, text, ResumeExtractionResult
        )

        name_ok = (result.full_name or "").strip().lower() == str(expected["full_name"]).lower()
        skill_score = _skills_overlap(result.skills, expected["expected_skills"])  # type: ignore[arg-type]
        name_matches += int(name_ok)
        skill_scores.append(skill_score)
        per_resume_results.append((filename, name_ok, skill_score))

    name_accuracy = name_matches / len(_GOLDEN_SET)
    avg_skill_overlap = sum(skill_scores) / len(skill_scores)

    print(
        f"\nGolden-set extraction accuracy: name={name_accuracy:.0%}, "
        f"avg_skill_overlap={avg_skill_overlap:.0%}"
    )
    for filename, name_ok, skill_score in per_resume_results:
        print(f"  {filename}: name_match={name_ok} skill_overlap={skill_score:.0%}")

    # Lenient thresholds — this catches regressions in extraction quality, not a demand for
    # perfection from a probabilistic model.
    assert name_accuracy >= 0.8
    assert avg_skill_overlap >= 0.5
