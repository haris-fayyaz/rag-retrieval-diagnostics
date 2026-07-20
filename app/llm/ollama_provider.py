import httpx

from app.llm.exceptions import LLMTemporaryError


class OllamaLLMProvider:
    """
    Real local LLM provider backed by Ollama (e.g. qwen3:1.7b).

    For manual local testing only - never used in CI or the automated
    test suite (those use FakeLLMProvider). Requires Ollama running
    locally first:

        ollama run qwen3:1.7b
    """

    def __init__(
        self,
        model: str = "qwen3:1.7b",
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            # Network error, timeout, Ollama not running, model not pulled, etc -
            # all collapse into one controlled error type for the endpoint to catch.
            raise LLMTemporaryError(f"Ollama request failed: {e}") from e

        data = response.json()
        answer = data.get("response", "").strip()
        if not answer:
            raise LLMTemporaryError("Ollama returned an empty response")
        return answer