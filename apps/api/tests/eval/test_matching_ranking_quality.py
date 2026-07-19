"""Golden-set eval for rerank ranking quality (Phase 4).

Makes real calls to Ollama Cloud, so it's skipped unless OLLAMA_API_KEY is set and it's not part
of the default CI `pytest` run (see .github/workflows/ci.yml) — run manually with:

    uv run pytest tests/eval -q -s

Small on purpose, same rationale as the Phase 2 extraction-accuracy eval — reuses the existing
golden resumes rather than a separate fixture set. Asserts *relative* ordering (a resume clearly
matching the role should outrank one that clearly doesn't), not an absolute score target, since
the LLM-based reranker (application/matching/scoring.py's design decision — Ollama Cloud has no
dedicated rerank endpoint) is inherently a fuzzy signal.
"""

from pathlib import Path

import pytest
from src.application.ai.ports import RerankCandidate
from src.core.config import get_settings
from src.infrastructure.ai.llm_reranker_client import LLMRerankerClient
from src.infrastructure.ai.ollama_client import OllamaClient

_GOLDEN_DIR = Path(__file__).parent / "golden_resumes"

_BACKEND_JOB_QUERY = """\
Senior Backend Engineer

We're looking for an experienced backend engineer to design and scale our core services.
Required skills: Python, PostgreSQL, distributed systems, cloud infrastructure (AWS or similar).
Responsibilities: own service architecture, mentor engineers, drive reliability improvements.\
"""

# (filename, expect_high_rank) — the strong match should outrank the clear mismatch.
_CANDIDATES = [
    ("001_backend_engineer.txt", True),
    ("005_marketing_manager.txt", False),
]


@pytest.mark.skipif(
    not get_settings().ollama_api_key,
    reason="OLLAMA_API_KEY not set — eval harness needs a real key",
)
def test_reranker_ranks_matching_resume_above_mismatched_resume() -> None:
    settings = get_settings()
    llm_client = OllamaClient(
        base_url=settings.ollama_base_url,
        api_key=settings.ollama_api_key,
        llm_model=settings.ollama_llm_model,
        embedding_model=settings.ollama_embedding_model,
    )
    reranker = LLMRerankerClient(llm_client)

    candidates = [
        RerankCandidate(id=filename, text=(_GOLDEN_DIR / filename).read_text())
        for filename, _ in _CANDIDATES
    ]

    results = {r.id: r.score for r in reranker.rerank(_BACKEND_JOB_QUERY, candidates)}

    print("\nRerank scores for Backend Engineer query:")
    for filename, _ in _CANDIDATES:
        print(f"  {filename}: {results.get(filename)}")

    backend_score = results["001_backend_engineer.txt"]
    marketing_score = results["005_marketing_manager.txt"]

    assert backend_score > marketing_score
