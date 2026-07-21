class LLMProviderError(Exception):
    """
    Base class for all LLM provider failures. answer_service catches
    this (or a specific subtype below) and turns it into a controlled
    HTTP error - never a raw stack trace.

    Prefer raising a specific subtype (LLMTemporaryError,
    LLMTimeoutError, LLMPermanentError) rather than this base class
    directly - the subtype is what tells answer_service whether the
    call is worth retrying.
    """
    pass


class LLMTemporaryError(LLMProviderError):
    """
    A transient failure that's worth retrying: connection refused,
    connection reset, a 5xx from the provider, etc. Something that
    might succeed if attempted again a moment later.
    """
    pass


class LLMTimeoutError(LLMTemporaryError):
    """
    The provider call exceeded the configured timeout
    (LLM_TIMEOUT_SECONDS). Treated as a specific kind of temporary
    failure - retryable, since the model may simply need another
    attempt (e.g. it was still loading).
    """
    pass


class LLMPermanentError(LLMProviderError):
    """
    A failure that retrying will not fix: malformed request, unknown
    model, invalid response shape. answer_service does not retry
    these - retrying a broken request just wastes time reproducing
    the same failure.
    """
    pass