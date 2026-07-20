from app.database.repositories.interface import DocumentRepository
from app.llm.provider import LLMProvider
from app.models import AnswerChunkRef, AnswerRequest, AnswerResponse
from app.services.retrieval import get_retriever

NO_CONTEXT_MESSAGE = "No relevant information was found in the selected documents."

# Fixed instructions prepended to every prompt - keeps the model grounded
# to only the supplied context. {example_id} is filled in per-request with
# a real chunk_id from the current retrieval (see _build_prompt) - a
# hardcoded example like "[doc_2_chunk_3]" taught the model to invent a
# "doc_" prefix that doesn't match our actual "{document_id}_chunk_{n}"
# scheme (e.g. "1_chunk_0"), even though it never affected correctness
# since citations are computed from retrieved chunks, not parsed from
# the model's text.
GROUNDING_INSTRUCTIONS_TEMPLATE = (
    "You must answer only from the supplied context.\n"
    "If the answer is not present, say that the available documents do not "
    "contain the answer.\n"
    "Cite supporting chunks using their IDs, for example:\n"
    "[{example_id}]"
)


def _build_prompt(question: str, retrieved_chunks: list) -> str:
    """Assemble the grounded prompt from only the chunks retrieval returned
    (never all stored chunks) - each chunk tagged with its ID so the model
    can cite it back."""
    context_blocks = [
        f"[{chunk.chunk_id}]\n{chunk.text_preview}" for chunk in retrieved_chunks
    ]
    context = "\n\n".join(context_blocks)

    instructions = GROUNDING_INSTRUCTIONS_TEMPLATE.format(
        example_id=retrieved_chunks[0].chunk_id
    )

    return (
        f"{instructions}\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{question}"
    )


def generate_answer(
    request: AnswerRequest,
    repo: DocumentRepository,
    provider: LLMProvider,
) -> AnswerResponse:
    """
    Question -> retrieve -> reject if no chunks -> grounded prompt -> LLM -> answer.

    Raises ValueError for empty question / unsupported retrieval mode -
    the endpoint maps these to HTTP 400. Lets LLMProviderError propagate
    unchanged - the endpoint maps that to HTTP 502.
    """
    if not request.question.strip():
        raise ValueError("Question cannot be empty")

    # Raises ValueError for an unknown mode (e.g. "tf-idf" typo) - the
    # endpoint turns this into a 400 instead of an unhandled 500.
    retriever = get_retriever(request.retrieval_mode)

    # Invalid/unknown document_ids simply match nothing here (same
    # behavior as /ask) - falls through to the no-context response below,
    # no special-casing needed.
    all_chunks = repo.get_chunks(request.document_ids)
    retrieved = (
        retriever.retrieve(request.question, all_chunks, request.top_k, request.min_score)
        if all_chunks
        else []
    )

    if not retrieved:
        return AnswerResponse(question=request.question, message=NO_CONTEXT_MESSAGE)

    prompt = _build_prompt(request.question, retrieved)
    answer = provider.generate(prompt)  # LLMProviderError propagates to the endpoint

    # Citations = every chunk actually sent as context. We ground strictly
    # on retrieved chunks, so all of them are valid sources - this is more
    # reliable than parsing "[chunk_id]" back out of free-form model text.
    citations = [chunk.chunk_id for chunk in retrieved]

    return AnswerResponse(
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
    )