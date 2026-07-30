"""
Optional LangChain-based answer pipeline (pipeline_mode="langchain").

Mirrors app/services/answer_service.py and prompt_builder.py's custom
path feature for feature: same hardened instructions, same
untrusted-context framing, citations still derived from retrieved
chunks only. Built with LangChain primitives instead: Document,
ChatPromptTemplate, LCEL (the `|` composition), and a swappable chat
model (FakeListChatModel for tests/CI, ChatOllama for manual runs
against the real Qwen model).

Kept isolated in this module on purpose. The custom pipeline in
answer_service.py/prompt_builder.py is untouched and remains the
default.
"""
from operator import itemgetter
from typing import List

import httpx
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_ollama import ChatOllama
from ollama import ResponseError as OllamaResponseError

from app.core.config import settings
from app.llm.exceptions import (
    LLMPermanentError,
    LLMProviderError,
    LLMTemporaryError,
    LLMTimeoutError,
)
from app.models import Chunk
from app.services.prompt_builder import (
    GROUNDEDNESS_INSTRUCTIONS,
    REFUSAL_INSTRUCTIONS,
    UNTRUSTED_DATA_INSTRUCTIONS,
)

_SYSTEM_INSTRUCTIONS = "\n\n".join([
    UNTRUSTED_DATA_INSTRUCTIONS,
    GROUNDEDNESS_INSTRUCTIONS,
    REFUSAL_INSTRUCTIONS,
    "Cite supporting chunks using their IDs, for example:\n[{example_id}]",
])

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_INSTRUCTIONS),
    ("human", "<untrusted_context>\n{context}\n</untrusted_context>\n\nQuestion:\n{question}"),
])


def to_documents(chunks: List[Chunk]) -> List[Document]:
    return [
        Document(
            page_content=chunk.text_preview,
            metadata={
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "score": chunk.score,
            },
        )
        for chunk in chunks
    ]


def _format_documents(documents: List[Document]) -> str:
    return "\n\n".join(
        f"[{doc.metadata['chunk_id']}]\n{doc.page_content}" for doc in documents
    )


def get_chat_model() -> BaseChatModel:
    if settings.llm_provider == "ollama":
        return ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            client_kwargs={"timeout": settings.llm_timeout_seconds},
        )
    return FakeListChatModel(responses=["This is a fake generated answer."])


def _build_chain(model: BaseChatModel):
    return (
        {
            "context": itemgetter("documents") | RunnableLambda(_format_documents),
            "question": itemgetter("question"),
            "example_id": itemgetter("example_id"),
        }
        | ANSWER_PROMPT
        | model
        | StrOutputParser()
    )


def _translate_exception(exc: Exception) -> LLMProviderError:
    if isinstance(exc, httpx.TimeoutException):
        return LLMTimeoutError(f"LangChain/Ollama request timed out: {exc}")
    if isinstance(exc, (httpx.ConnectError, ConnectionError)):
        return LLMTemporaryError(f"Could not connect to Ollama via LangChain: {exc}")
    if isinstance(exc, OllamaResponseError):
        if exc.status_code >= 500:
            return LLMTemporaryError(f"Ollama server error via LangChain ({exc.status_code}): {exc}")
        return LLMPermanentError(f"Ollama rejected the request via LangChain ({exc.status_code}): {exc}")
    return LLMTemporaryError(f"LangChain pipeline request failed: {exc}")


def generate_answer_via_langchain(model: BaseChatModel, question: str, retrieved_chunks: List[Chunk]) -> str:
    documents = to_documents(retrieved_chunks)
    chain = _build_chain(model)
    try:
        return chain.invoke({
            "documents": documents,
            "question": question,
            "example_id": retrieved_chunks[0].chunk_id,
        })
    except (LLMPermanentError, LLMTemporaryError):
        raise
    except Exception as e:
        raise _translate_exception(e) from e