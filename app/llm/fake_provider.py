from typing import Optional, Type

from app.llm.exceptions import LLMProviderError, LLMTemporaryError


class FakeLLMProvider:
    """
    Deterministic stand-in for a real LLM. No network calls - safe for
    CI and automated tests.

    - `response`: fixed text returned once failures (if any) are exhausted.
    - `fail`: if True, every call fails (unconditional outage) - kept for
      backward compatibility with existing tests.
    - `fail_times`: number of calls that should fail before generate()
      starts succeeding. E.g. fail_times=1 fails on attempt 1, succeeds
      on attempt 2 - lets tests exercise "retry then succeed" without a
      real provider.
    - `error`: the exception type raised while failing (default
      LLMTemporaryError). Pass LLMPermanentError to test "never retried",
      or LLMTimeoutError to test the timeout-specific path.
    - `last_prompt`: captures the most recent prompt sent, so tests can
      assert the grounded prompt was built correctly (e.g. contains the
      right chunk IDs / context) without needing a real model.
    - `call_count`: increments on every generate() call, so tests can
      assert the provider was called the expected number of times - e.g.
      proving a no-context request skips the LLM entirely (0 calls), or
      that a retry actually happened (2 calls).
    """

    def __init__(
        self,
        response: str = "This is a fake generated answer.",
        fail: bool = False,
        fail_times: int = 0,
        error: Type[LLMProviderError] = LLMTemporaryError,
    ):
        self.response = response
        self.fail = fail
        self.fail_times = fail_times
        self.error = error
        self.last_prompt: Optional[str] = None
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        if self.fail or self.call_count <= self.fail_times:
            raise self.error(f"Simulated provider failure (attempt {self.call_count})")
        return self.response