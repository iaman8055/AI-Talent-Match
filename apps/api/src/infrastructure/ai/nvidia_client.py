import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

_T = TypeVar("_T", bound=BaseModel)


def _extract_json_object(content: str) -> dict[str, object]:
    """NVIDIA-hosted reasoning models can occasionally wrap the JSON answer in prose or markdown
    fences despite instructions not to — this recovers the JSON object substring rather than
    failing outright on an otherwise-correct response."""
    try:
        parsed: dict[str, object] = json.loads(content)
        return parsed
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise
        parsed = json.loads(content[start : end + 1])
        return parsed


class NvidiaClient:
    """Implements LLMClient + EmbeddingClient against NVIDIA's hosted inference API
    (https://integrate.api.nvidia.com/v1) — an OpenAI-compatible chat completions + embeddings
    endpoint, per docs/02-ARCHITECTURE.md §4's "swappable client interface" for the AI layer
    (same ports as infrastructure/ai/ollama_client.py's OllamaClient, different wire format).

    `extract_structured`'s `instructions`/`data` split is the prompt-injection guard required by
    docs/01-ANALYSIS.md gap #6: they're always sent as separate system/user messages, never
    concatenated, so untrusted resume/JD text can never masquerade as instructions. The target
    JSON schema is appended to `instructions` (trusted, caller-supplied), never to `data`.
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
            raise ValueError("NVIDIA_API_KEY is not set — configure it before calling NVIDIA's API")
        return {"Authorization": f"Bearer {self._api_key}"}

    def extract_structured(self, instructions: str, data: str, schema: type[_T]) -> _T:
        schema_instructions = (
            f"{instructions}\n\n"
            "Respond with ONLY a single JSON object conforming to this JSON schema — no prose, "
            "no markdown code fences, no explanation, just the JSON object:\n"
            f"{schema.model_json_schema()}"
        )
        payload = {
            "model": self._llm_model,
            "messages": [
                {"role": "system", "content": schema_instructions},
                {"role": "user", "content": data},
            ],
            "temperature": 0.2,
            "max_tokens": 8192,
            # Nemotron-family reasoning models support an extended "thinking" mode — disabled
            # here so the response is the direct JSON answer, not a chain-of-thought preamble.
            # (This must be a top-level field on the wire — "extra_body" is an OpenAI *SDK-only*
            # convenience wrapper that merges its contents into the request body; it isn't a real
            # API field, and sending it literally causes NVIDIA's API to reject the request.)
            "chat_template_kwargs": {"enable_thinking": False},
            "stream": False,
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=self._headers()
            )
            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"{response.status_code} error from NVIDIA API: {response.text}",
                    request=response.request,
                    response=response,
                )

        content = response.json()["choices"][0]["message"]["content"]
        return schema.model_validate(_extract_json_object(content))

    def embed(self, texts: list[str]) -> list[list[float]]:
        # NV-EmbedQA-family models require input_type ("query" vs "passage") to know which side
        # of a retrieval pair they're embedding. We use them symmetrically — both resumes and
        # jobs are indexed documents compared via cosine similarity, never a live search query —
        # so "passage" is the correct constant for every call, not a per-caller choice.
        payload = {"model": self._embedding_model, "input": texts, "input_type": "passage"}
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self._base_url}/embeddings", json=payload, headers=self._headers()
            )
            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"{response.status_code} error from NVIDIA API: {response.text}",
                    request=response.request,
                    response=response,
                )

        items = sorted(response.json()["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in items]
