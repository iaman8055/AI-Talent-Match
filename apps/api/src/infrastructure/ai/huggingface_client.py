import httpx

_INFERENCE_URL = (
    "https://router.huggingface.co/hf-inference/models/{model}/pipeline/feature-extraction"
)


class HuggingFaceEmbeddingClient:
    """Implements EmbeddingClient against the Hugging Face Inference API — used only for
    embeddings (BAAI/bge-m3 by default), keeping the highest-volume AI call (every resume/job
    embed) off the NVIDIA-shared rate limit budget entirely. NVIDIA remains the LLM/rerank
    provider (infrastructure/ai/nvidia_client.py) — this is additive, not a swap of that client.

    Endpoint confirmed directly against the live API: the older api-inference.huggingface.co
    host no longer resolves — HF's current routed inference API is
    router.huggingface.co/hf-inference/models/{model}/pipeline/feature-extraction, POSTing
    {"inputs": [...]} and getting back a list of embedding vectors, one per input, in order.
    """

    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ValueError(
                "HUGGINGFACE_API_KEY is not set — configure it before calling Hugging Face's API"
            )
        return {"Authorization": f"Bearer {self._api_key}"}

    def embed(self, texts: list[str]) -> list[list[float]]:
        url = _INFERENCE_URL.format(model=self._model)
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json={"inputs": texts}, headers=self._headers())
            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"{response.status_code} error from Hugging Face API: {response.text}",
                    request=response.request,
                    response=response,
                )

        return list(response.json())
