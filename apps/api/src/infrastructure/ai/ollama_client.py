import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

_T = TypeVar("_T", bound=BaseModel)


class OllamaClient:
    """Implements LLMClient + EmbeddingClient against either a local Ollama install
    (`ollama serve`, no auth) or Ollama Cloud (https://ollama.com, bearer token) — same REST
    surface either way, per docs/02-ARCHITECTURE.md §4's "swappable client interface" for the AI
    layer. Which one you're talking to is entirely a matter of OLLAMA_BASE_URL/OLLAMA_API_KEY:
    point base_url at http://localhost:11434 and leave api_key unset for local; point it at
    https://ollama.com and set api_key for Cloud.

    `extract_structured`'s `instructions`/`data` split is the prompt-injection guard required by
    docs/01-ANALYSIS.md gap #6: they're always sent as separate system/user messages, never
    concatenated, so untrusted resume/JD text can never masquerade as instructions.
    """

    def __init__(
        self, base_url: str, api_key: str | None, llm_model: str, embedding_model: str
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._llm_model = llm_model
        self._embedding_model = embedding_model

    def _headers(self) -> dict[str, str]:
        # No key configured is a valid, expected state for a local Ollama install (it has no
        # auth) — only Cloud needs a bearer token, so this omits the header rather than erroring.
        if not self._api_key:
            return {}
        return {"Authorization": f"Bearer {self._api_key}"}

    def extract_structured(self, instructions: str, data: str, schema: type[_T]) -> _T:
        payload = {
            "model": self._llm_model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": data},
            ],
            "format": schema.model_json_schema(),
            "stream": False,
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self._base_url}/api/chat", json=payload, headers=self._headers()
            )
            response.raise_for_status()

        content = response.json()["message"]["content"]
        return schema.model_validate(json.loads(content))

    def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self._embedding_model, "input": texts}
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self._base_url}/api/embed", json=payload, headers=self._headers()
            )
            response.raise_for_status()

        embeddings: list[list[float]] = response.json()["embeddings"]
        return embeddings
