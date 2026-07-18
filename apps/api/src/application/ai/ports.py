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


class VectorStore(Protocol):
    def ensure_collection(self, collection: str, vector_size: int) -> None: ...

    def upsert(
        self, collection: str, point_id: str, vector: list[float], payload: dict[str, object]
    ) -> None: ...

    def delete(self, collection: str, point_id: str) -> None: ...
