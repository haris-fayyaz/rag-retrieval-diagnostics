import httpx

from app.llm.exceptions import LLMTemporaryError, LLMTimeoutError, LLMPermanentError


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
        except httpx.TimeoutException as e:
            # Took longer than self.timeout - may just need another
            # attempt (e.g. model still warming up). Retryable.
            raise LLMTimeoutError(f"Ollama request timed out after {self.timeout}s: {e}") from e
        except httpx.ConnectError as e:
            # Ollama isn't reachable right now - may come back shortly.
            # Retryable.
            raise LLMTemporaryError(f"Could not connect to Ollama: {e}") from e
        except httpx.HTTPStatusError as e:
            # 5xx = Ollama's own server error - worth retrying. 4xx = we
            # sent something wrong (bad model name, malformed request) -
            # retrying resends the exact same bad request, so don't.
            status = e.response.status_code if e.response is not None else None
            if status is not None and status >= 500:
                raise LLMTemporaryError(f"Ollama server error ({status}): {e}") from e
            raise LLMPermanentError(f"Ollama rejected the request ({status}): {e}") from e
        except httpx.HTTPError as e:
            # Any other httpx-level failure not specifically classified
            # above - default to temporary. Blocking a retry on an
            # unrecognized error is riskier than one extra attempt.
            raise LLMTemporaryError(f"Ollama request failed: {e}") from e

        data = response.json()
        answer = data.get("response", "").strip()
        if not answer:
            # A 200 OK with no text isn't a network problem - retrying
            # the identical request would very likely produce the same
            # empty response. Not retryable.
            raise LLMPermanentError("Ollama returned an empty response")
        return answer