from typing import Protocol


class LLMProvider(Protocol):
    """
    Boundary between answer_service and any specific LLM backend.

    answer_service only ever calls .generate(prompt) - it never knows
    or cares whether that's a fake, Ollama, OpenAI, Anthropic, etc.
    Same pattern as DocumentRepository: depend on the interface, not
    the implementation.
    """

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to the LLM and return its raw text response.

        Implementations should raise LLMProviderError (not a bare
        Exception) on failure, so callers can handle it as a known,
        controlled error rather than an unhandled exception.
        """
        ...


class LLMProviderError(Exception):
    """Raised when an LLM provider fails to produce a response
    (network error, timeout, bad response, etc). answer_service
    catches this and turns it into a clean HTTP error - never a
    raw stack trace."""
    pass