from dataclasses import dataclass, field
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    def extract_structured(self, instructions: str, data: str, schema: type[T]) -> T:
        """`instructions` must always be a hardcoded, trusted caller string — never untrusted
        content. `data` is the untrusted input (e.g. resume text) and is never concatenated into
        `instructions`; implementations must keep them in separate message roles so every call
        site gets prompt-injection guarding automatically."""
        ...


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class VectorFilter:
    """A small, provider-agnostic filter shape — adapters (e.g. QdrantVectorStore) translate
    this into their own filter DSL rather than leaking it into application code."""

    equals: dict[str, object] = field(default_factory=dict)
    gte: dict[str, float] = field(default_factory=dict)
    lte: dict[str, float] = field(default_factory=dict)


@dataclass
class VectorSearchResult:
    point_id: str
    score: float
    payload: dict[str, object]


class VectorStore(Protocol):
    def ensure_collection(self, collection: str, vector_size: int) -> None: ...

    def upsert(
        self, collection: str, point_id: str, vector: list[float], payload: dict[str, object]
    ) -> None: ...

    def delete(self, collection: str, point_id: str) -> None: ...

    def get_vector(self, collection: str, point_id: str) -> list[float] | None: ...

    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int,
        query_filter: VectorFilter | None = None,
    ) -> list[VectorSearchResult]: ...


@dataclass
class RerankCandidate:
    id: str
    text: str


@dataclass
class RerankResult:
    id: str
    score: float
    reasoning: str | None = None


class RerankerClient(Protocol):
    def rerank(self, query: str, candidates: list[RerankCandidate]) -> list[RerankResult]:
        """Returns one result per input candidate (order not guaranteed to match input order).
        `query` and `candidates` text are both derived content (job/resume text, already
        AI-parsed), never hardcoded instructions — implementations must keep them out of any
        system/instructions role, same prompt-injection contract as
        `LLMClient.extract_structured`."""
        ...
