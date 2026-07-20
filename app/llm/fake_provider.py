from typing import Optional

from app.llm.provider import LLMProviderError


class FakeLLMProvider:
    """
    Deterministic stand-in for a real LLM. No network calls - safe for
    CI and automated tests.
 
    - `response`: fixed text returned by every call to generate().
    - `fail`: if True, simulates a provider outage by raising
      LLMProviderError instead of returning text.
    - `last_prompt`: captures the most recent prompt sent, so tests can
      assert the grounded prompt was built correctly (e.g. contains the
      right chunk IDs / context) without needing a real model.
    - `call_count`: increments on every generate() call, so tests can
      assert the provider was (or crucially, was NOT) invoked - e.g.
      proving the no-context path skips the LLM entirely.
    """

    def __init__(self, response: str = "This is a fake generated answer.", fail: bool = False):
        self.response = response
        self.fail = fail
        self.last_prompt: Optional[str] = None
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        if self.fail:
            raise LLMProviderError("Simulated provider failure")
        return self.response