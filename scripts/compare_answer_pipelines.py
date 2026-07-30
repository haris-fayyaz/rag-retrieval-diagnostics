"""
Run the same questions through both pipeline_mode values against the
same documents/settings, and print a comparison table.

Usage:
    python scripts/compare_answer_pipelines.py

Uses an in-memory SQLite DB and the fake providers/models (no network,
no Ollama) so this runs anywhere, same constraint as the default test
suite. To compare against real Ollama output instead, set
LLM_PROVIDER=ollama before running.
"""
import sys
import time
from pathlib import Path
 
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.chains.langchain_answer_chain import get_chat_model
from app.core.config import settings
from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.llm.ollama_provider import OllamaLLMProvider
from app.models import AnswerRequest
from app.services.answer_service import generate_answer

DOCUMENTS = [
    ("it_policy.txt", "Employees may claim laptop reimbursement up to $800 per year. Requests go through IT."),
    ("leave_policy.txt", "Full-time staff get 20 paid leave days annually. Unused days do not carry over."),
    ("security_policy.txt", "All laptops must have disk encryption enabled before leaving the office."),
]

CASES = [
    "What is the laptop reimbursement limit?",
    "How many paid leave days do employees get?",
    "Do unused leave days carry over?",
    "What security requirement applies to laptops?",
    "What is the capital of France?",  # expected: no_context, off-topic
]


def _build_provider():
    return OllamaLLMProvider() if settings.llm_provider == "ollama" else FakeLLMProvider(
        response="Reimbursement is capped at $800 per year. [1_chunk_0]"
    )


def run():
    repo = SQLiteDocumentRepository("sqlite:///:memory:")
    Base.metadata.create_all(repo.engine)
    from app.services.chunking_service import chunk_text
    for name, text in DOCUMENTS:
        repo.create_document_with_chunks(name, text, chunk_text)

    provider = _build_provider()
    langchain_model = get_chat_model()

    rows = []
    for question in CASES:
        row = {"question": question}
        for mode in ("custom", "langchain"):
            req = AnswerRequest(question=question, pipeline_mode=mode)
            start = time.perf_counter()
            resp = generate_answer(req, repo, provider, langchain_model, f"compare-{mode}")
            elapsed_ms = (time.perf_counter() - start) * 1000
            row[mode] = {
                "chunks": [c.chunk_id for c in resp.retrieved_chunks],
                "citations": resp.citations,
                "grounded": bool(resp.citations),
                "ms": round(elapsed_ms, 1),
            }
        rows.append(row)

    print(f"{'Question':<45} {'Custom Chunks':<20} {'LangChain Chunks':<20} {'Same Chunks':<12} {'Same Citations':<14}")
    for row in rows:
        cust, lc = row["custom"], row["langchain"]
        print(
            f"{row['question'][:44]:<45} {str(cust['chunks'])[:19]:<20} {str(lc['chunks'])[:19]:<20} "
            f"{str(cust['chunks'] == lc['chunks']):<12} {str(cust['citations'] == lc['citations']):<14}"
        )
    return rows


if __name__ == "__main__":
    run()
    