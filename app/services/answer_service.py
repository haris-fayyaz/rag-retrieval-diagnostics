import time
from typing import Callable

from app.core.config import settings
from app.core.logging import get_logger, log_event
from app.database.repositories.interface import DocumentRepository
from app.llm.exceptions import LLMPermanentError, LLMTemporaryError
from app.llm.provider import LLMProvider
from app.models import AnswerChunkRef, AnswerRequest, AnswerResponse, AnswerMetadata

from langchain_core.language_models.chat_models import BaseChatModel

from app.chains.langchain_answer_chain import generate_answer_via_langchain
from app.services.retrieval import get_retriever
from app.services.prompt_builder import build_prompt

logger = get_logger()

NO_CONTEXT_MESSAGE = "No relevant information was found in the selected documents."


def _call_with_retry(call: Callable[[], str], request_id: str) -> str:
    """
    Call `call()`, retrying only genuinely transient failures - up to
    settings.llm_max_retries additional attempts after the first.

    Generalized from the original provider.generate(prompt)-only version
    to any zero-arg callable, so both the custom pipeline
    (lambda: provider.generate(prompt)) and the LangChain pipeline
    (lambda: generate_answer_via_langchain(...)) share this one retry
    implementation - retry/timeout behavior is identical across both
    pipelines because it's the same code, not two copies kept in sync
    by hand.

    - LLMPermanentError: never retried. Propagates on the first attempt.
      Retrying an identical bad request (unknown model, malformed input)
      just reproduces the same failure - it wastes time and a retry
      "slot" on something a second attempt cannot fix.
    - LLMTemporaryError (and its subtype LLMTimeoutError): retried, since
      these represent conditions that may resolve on their own (brief
      network blip, provider momentarily busy, cold-start timeout).
    - Once attempts are exhausted, the last temporary failure propagates
      unchanged - the endpoint still maps it to a controlled 502, this
      function only decides *how many times* to try, not how to report
      failure.

    Retries are capped by settings.llm_max_retries (env: LLM_MAX_RETRIES) -
    this can never loop indefinitely, by construction: the for-loop range
    is fixed before the first call is made.
    """
    max_attempts = settings.llm_max_retries + 1

    for attempt in range(1, max_attempts + 1):
        log_event(logger, "llm_attempt_started", request_id=request_id, attempt=attempt, max_attempts=max_attempts)
        try:
            return call()
        except LLMPermanentError as e:
            log_event(
                logger, "provider_failed", request_id=request_id, attempt=attempt,
                error_type=type(e).__name__, retryable=False,
            )
            raise
        except LLMTemporaryError as e:
            log_event(
                logger, "provider_failed", request_id=request_id, attempt=attempt,
                error_type=type(e).__name__, retryable=True,
            )
            if attempt == max_attempts:
                raise
            log_event(
                logger, "retry_triggered", request_id=request_id,
                next_attempt=attempt + 1, max_attempts=max_attempts,
            )

def _provider_name(provider: LLMProvider) -> str:
    """
    Human-readable provider name for response metadata and logs, derived
    from the class name rather than requiring every provider to define
    its own name attribute: FakeLLMProvider -> "fake",
    OllamaLLMProvider -> "ollama".
    """
    class_name = type(provider).__name__
    return class_name.removesuffix("LLMProvider").lower() or class_name.lower()

def _langchain_provider_name(model: BaseChatModel) -> str:
    """
    Same idea as _provider_name() above, but for the LangChain pipeline's
    chat model. Deliberately returns the SAME vocabulary ("fake" /
    "ollama") rather than e.g. "langchain-ollama" - the audit "provider"
    field means "which backend", the separate "pipeline_mode" field
    means "which code path". Keeping provider names identical across
    both lets the comparison script filter by pipeline_mode and compare
    same-provider runs directly.
    """
    class_name = type(model).__name__
    if class_name == "ChatOllama":
        return "ollama"
    if class_name == "FakeListChatModel":
        return "fake"
    return class_name.lower()

def _record_audit(repo: DocumentRepository, request_id: str, **fields) -> None:
    """
    Best-effort audit write. Deliberately swallows any exception - a
    broken audit write (e.g. a locked DB file) must never turn a
    successful /answer call into a failure, per the task's requirement
    that "audit persistence should not change the existing API response
    behavior". Failures are logged so they're still visible, just not
    surfaced to the caller.
    """
    try:
        repo.save_answer_run(request_id=request_id, **fields)
    except Exception as e:
        log_event(logger, "audit_write_failed", request_id=request_id, error_type=type(e).__name__)

def generate_answer(
    request: AnswerRequest,
    repo: DocumentRepository,
    provider: LLMProvider,
    langchain_model: BaseChatModel,
    request_id: str,
) -> AnswerResponse:
    """
    Question -> retrieve -> reject if no chunks -> grounded prompt -> LLM -> answer.

    Retrieval, no-context handling, citations, and audit are identical
    regardless of request.pipeline_mode - only how the answer text
    itself gets generated differs (see the pipeline_mode branch below).

    `request_id` is generated by the endpoint (not here) - it needs to be
    available even when this function raises before ever building a
    response, so the endpoint can attach it to the error it returns too.

    Raises ValueError for empty question / unsupported retrieval mode -
    the endpoint maps these to HTTP 400. Lets LLMProviderError propagate
    unchanged - the endpoint maps that to HTTP 502.
    """
    total_start = time.perf_counter()
    log_event(logger, "answer_request_started", request_id=request_id, retrieval_mode=request.retrieval_mode)

    if not request.question.strip():
        raise ValueError("Question cannot be empty")

    # Raises ValueError for an unknown mode (e.g. "tf-idf" typo) - the
    # endpoint turns this into a 400 instead of an unhandled 500.
    retriever = get_retriever(request.retrieval_mode)

    # provider/model naming depends on which pipeline would run the
    # generation step - resolved once, up front, since both the
    # no-context audit (below) and the success/error audit (further
    # down) need the same values regardless of outcome.
    if request.pipeline_mode == "langchain":
        provider_name = _langchain_provider_name(langchain_model)
        model_name = getattr(langchain_model, "model", None)
    else:
        provider_name = _provider_name(provider)
        model_name = getattr(provider, "model", None)

    # Retrieval timing covers fetching persisted chunks AND scoring them -
    # both are part of "how long did finding relevant context take".
    retrieval_start = time.perf_counter()
    all_chunks = repo.get_chunks(request.document_ids)
    retrieved = (
        retriever.retrieve(request.question, all_chunks, request.top_k, request.min_score)
        if all_chunks
        else []
    )
    retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
    log_event(
        logger, "retrieval_completed", request_id=request_id,
        retrieval_mode=request.retrieval_mode, retrieved_chunk_count=len(retrieved),
        retrieval_ms=retrieval_ms,
    )

    if not retrieved:
        log_event(logger, "no_context_found", request_id=request_id, retrieval_mode=request.retrieval_mode)
        no_context_total_ms = (time.perf_counter() - total_start) * 1000
        _record_audit(
            repo, request_id, question=request.question, answer=None, status="no_context",
            retrieval_mode=request.retrieval_mode, top_k=request.top_k, min_score=request.min_score,
            provider=provider_name, model=model_name,
            retrieved_chunk_ids=[], citations=[],
            retrieval_ms=retrieval_ms, generation_ms=None, total_ms=no_context_total_ms,
        )
        return AnswerResponse(
            request_id=request_id,
            question=request.question,
            message=NO_CONTEXT_MESSAGE,
            metadata=AnswerMetadata(
                retrieval_ms=retrieval_ms,
                generation_ms=None,  # LLM was never called
                total_ms=no_context_total_ms,
                retrieved_chunk_count=0,
                retrieval_mode=request.retrieval_mode,
                provider=provider_name,
            ),
        )

    # pipeline_mode picks HOW the answer text is generated - everything
    # else (retrieval above, citations/audit below) is shared. custom
    # builds the same hand-rolled prompt string as before; langchain
    # builds LangChain Documents and runs the LCEL chain instead - see
    # app/chains/langchain_answer_chain.py. Either way, `call` is a
    # zero-arg callable so _call_with_retry doesn't need to know which
    # pipeline it's retrying.
    if request.pipeline_mode == "langchain":
        def call() -> str:
            return generate_answer_via_langchain(langchain_model, request.question, retrieved)
    else:
        prompt = build_prompt(request.question, retrieved)

        def call() -> str:
            return provider.generate(prompt)


    generation_start = time.perf_counter()
    try:
        answer = _call_with_retry(call, request_id)  # LLMProviderError propagates to the endpoint
    except Exception:
        _record_audit(
            repo, request_id, question=request.question, answer=None, status="provider_error",
            retrieval_mode=request.retrieval_mode, top_k=request.top_k, min_score=request.min_score,
            provider=provider_name, model=model_name,
            retrieved_chunk_ids=[chunk.chunk_id for chunk in retrieved], citations=[],
            retrieval_ms=retrieval_ms, generation_ms=(time.perf_counter() - generation_start) * 1000,
            total_ms=(time.perf_counter() - total_start) * 1000,
        )
        raise
    generation_ms = (time.perf_counter() - generation_start) * 1000

    # Citations = every chunk actually sent as context. We ground strictly
    # on retrieved chunks, so all of them are valid sources - this is more
    # reliable than parsing "[chunk_id]" back out of free-form model text.
    citations = [chunk.chunk_id for chunk in retrieved]
    total_ms = (time.perf_counter() - total_start) * 1000
    log_event(
        logger, "answer_completed", request_id=request_id, retrieval_mode=request.retrieval_mode,
        retrieved_chunk_count=len(retrieved), retrieval_ms=retrieval_ms,
        generation_ms=generation_ms, total_ms=total_ms,
    )
    _record_audit(
        repo, request_id, question=request.question, answer=answer, status="success",
        retrieval_mode=request.retrieval_mode, top_k=request.top_k, min_score=request.min_score,
        provider=provider_name, model=model_name,
        retrieved_chunk_ids=[chunk.chunk_id for chunk in retrieved], citations=citations,
        retrieval_ms=retrieval_ms, generation_ms=generation_ms, total_ms=total_ms,
    )

    return AnswerResponse(
        request_id=request_id,
        question=request.question,
        answer=answer,
        citations=citations,
        retrieved_chunks=[
            AnswerChunkRef(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                score=chunk.score,
            )
            for chunk in retrieved
        ],
        metadata=AnswerMetadata(
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms,
            total_ms=total_ms,  # now reuses the value computed above, instead of calling perf_counter() again
            retrieved_chunk_count=len(retrieved),
            retrieval_mode=request.retrieval_mode,
            provider=provider_name,
        ),
    )