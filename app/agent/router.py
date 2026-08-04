"""
Query routers for the document assistant graph.

route(query) returns one of VALID_TOOLS, or None to mean "refuse" -
the request is out of scope (write actions, unrelated topics, or too
ambiguous to route safely). Refusal is a first-class outcome, not an
error - it's how the graph avoids guessing.
"""

from typing import Optional, Protocol

from app.core.logging import get_logger, log_event
from app.llm.exceptions import LLMProviderError
from app.llm.provider import LLMProvider

logger = get_logger()

VALID_TOOLS = {"search_documents", "list_documents", "get_answer_run"}


class QueryRouter(Protocol):
    def route(self, query: str) -> Optional[str]:
        """Return a tool name from VALID_TOOLS, or None to refuse."""
        ...


class RuleBasedRouter:
    """
    Deterministic, offline router - no LLM call. This is what every
    automated test in this suite uses, and the default in production
    when LLM_PROVIDER=fake. Simple by design: a fixed, extensible
    keyword ruleset, not an attempt at real NLU.
    """

    _LIST_KEYWORDS = (
        "list documents", "available documents", "what documents",
        "show documents", "which documents",
    )
    _AUDIT_KEYWORDS = (
        "request id", "request_id", "audit", "previous answer",
        "past answer", "earlier run",
    )
    # Actions this agent deliberately cannot perform (read-only by design).
    _WRITE_KEYWORDS = (
        "delete", "remove", "update", "edit", "modify", "reindex",
        "re-index", "upload", "insert", "overwrite",
    )
    # Clearly out of scope for a document assistant.
    _OFF_TOPIC_KEYWORDS = ("weather", "joke", "poem", "song", "recipe", "translate")

    def route(self, query: str) -> Optional[str]:
        normalized = query.strip().lower()
        if not normalized:
            return None

        if any(kw in normalized for kw in self._WRITE_KEYWORDS):
            return None
        if any(kw in normalized for kw in self._OFF_TOPIC_KEYWORDS):
            return None
        if any(kw in normalized for kw in self._LIST_KEYWORDS):
            return "list_documents"
        if any(kw in normalized for kw in self._AUDIT_KEYWORDS):
            return "get_answer_run"

        # Default: treat as a document question if it has enough
        # content to plausibly be one. Single-word/very short input
        # is too ambiguous to confidently route - refuse instead of guessing.
        if len(normalized.split()) >= 3:
            return "search_documents"
        return None


class OllamaRouter:
    """
    LLM-backed router for manual testing against a real model (Qwen via
    Ollama) - per task spec, not used in the automated test suite.

    Any output outside the 4 allowed labels (malformed, hallucinated,
    or a provider failure) falls back to `fallback`. This is the safe
    fallback the task requires: an unreliable model output can never
    select an invalid tool.
    """

    _ALLOWED_LABELS = VALID_TOOLS | {"unsupported"}

    _PROMPT_TEMPLATE = (
        "Classify the request into exactly one label. "
        "Respond with ONLY the label, nothing else.\n\n"
        "Labels:\n"
        "- search_documents: a question about the content of documents\n"
        "- list_documents: a request to see what documents are available\n"
        "- get_answer_run: a request to inspect a previous answer by its request ID\n"
        "- unsupported: anything else (write requests, unrelated topics, unclear requests)\n\n"
        "Request: {query}\n"
        "Label:"
    )

    def __init__(self, llm_provider: LLMProvider, fallback: QueryRouter):
        self._llm_provider = llm_provider
        self._fallback = fallback

    def route(self, query: str) -> Optional[str]:
        prompt = self._PROMPT_TEMPLATE.format(query=query)
        try:
            raw_response = self._llm_provider.generate(prompt)
        except LLMProviderError as exc:
            log_event(logger, "router_llm_call_failed", error=str(exc))
            return self._fallback.route(query)

        label = raw_response.strip().lower()
        if label not in self._ALLOWED_LABELS:
            log_event(logger, "router_llm_invalid_label", raw_label=label)
            return self._fallback.route(query)

        log_event(logger, "router_llm_selected", label=label)
        return None if label == "unsupported" else label


def build_router(llm_provider: LLMProvider, use_llm: bool) -> QueryRouter:
    """
    use_llm=True (settings.llm_provider == "ollama") wraps the real
    model with a safe fallback to RuleBasedRouter. Otherwise routing
    is fully deterministic - this is what keeps the default test suite
    offline and reproducible.
    """
    fallback = RuleBasedRouter()
    if use_llm:
        return OllamaRouter(llm_provider=llm_provider, fallback=fallback)
    return fallback