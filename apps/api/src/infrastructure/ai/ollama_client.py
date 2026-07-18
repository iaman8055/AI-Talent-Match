import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

_T = TypeVar("_T", bound=BaseModel)


class OllamaClient:
    """Implements LLMClient + EmbeddingClient against Ollama Cloud (https://ollama.com). Same
    REST surface as a local Ollama install, just pointed at the cloud host with a bearer token.

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
        if not self._api_key:
            raise ValueError("OLLAMA_API_KEY is not set — configure it before calling Ollama Cloud")
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
