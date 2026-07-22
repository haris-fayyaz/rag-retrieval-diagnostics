"""
Manual evaluation harness for /answer's groundedness and prompt-injection
resistance.

This is NOT part of automated CI and does NOT use another LLM as a judge
(per the task's requirement). It's meant to be run locally against a real
Ollama model, with a human then reading each answer and filling in the
"Manual groundedness result" column by hand - see eval/groundedness_report.md.

Usage:
    python -m scripts.evaluate_answers            # real Ollama (uses LLM_MODEL / OLLAMA_BASE_URL / LLM_TIMEOUT_SECONDS from env)
    python -m scripts.evaluate_answers --fake      # quick smoke test with FakeLLMProvider, no Ollama needed - proves the harness itself works, NOT a real groundedness result
"""

import json
import os
import sys
import tempfile
import uuid

from app.core.config import settings
from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.llm.ollama_provider import OllamaLLMProvider
from app.models import AnswerRequest
from app.services.answer_service import generate_answer
from app.services.chunking_service import chunk_text

CASES_FILE = "eval/answer_eval_cases.json"


def load_cases(filepath: str = CASES_FILE) -> dict:
    with open(filepath) as f:
        return json.load(f)


def make_scratch_repo() -> SQLiteDocumentRepository:
    """
    A real temp-file SQLite DB, not ':memory:' - an in-memory DB is
    per-connection, so a session opened later (as every repository method
    does) would see an empty database, not the one we just seeded here.
    """
    tmp_dir = tempfile.mkdtemp(prefix="answer_eval_")
    db_path = os.path.join(tmp_dir, "eval.db")
    repo = SQLiteDocumentRepository(f"sqlite:///{db_path}")
    Base.metadata.create_all(repo.engine)
    return repo


def seed_documents(repo: SQLiteDocumentRepository, documents: list) -> dict:
    """Insert every eval document, return {doc_key: numeric_document_id}
    so cases (which reference documents by their human-readable "id",
    e.g. "hr_policy") can be translated into real document_ids for
    AnswerRequest."""
    id_map = {}
    for doc in documents:
        response = repo.create_document_with_chunks(doc["name"], doc["text"], chunk_text)
        id_map[doc["id"]] = response.document_id
    return id_map


def build_provider(use_fake: bool):
    if use_fake:
        return FakeLLMProvider(response="[fake provider output - not a real groundedness result]")
    return OllamaLLMProvider(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        timeout=settings.llm_timeout_seconds,
    )


def run_case(case: dict, repo, provider, id_map: dict) -> dict:
    """Run one eval case through the real /answer pipeline (generate_answer,
    same function the API calls) and collect what's needed for the report."""
    document_ids = [id_map[key] for key in case["document_ids"]] if case["document_ids"] else None

    request = AnswerRequest(
        question=case["question"],
        document_ids=document_ids,
        top_k=3,
        min_score=0.1,
        retrieval_mode="tfidf",
    )

    try:
        response = generate_answer(request, repo, provider, request_id=str(uuid.uuid4()))
        did_answer = response.answer is not None
        citations = response.citations
        answer_text = response.answer
        cited_doc_keys = sorted(
            key for chunk in response.retrieved_chunks
            for key, doc_id in id_map.items() if doc_id == chunk.document_id
        )
    except Exception as e:
        did_answer, citations, answer_text, cited_doc_keys = False, [], f"[ERROR: {e}]", []

    expected_docs = set(case["expected_documents"])
    cited_docs = set(cited_doc_keys)
    # A citation from a document outside the expected set is worth flagging
    # for manual review either way: for a should_answer=true case it may
    # signal an unrelated chunk snuck in; for should_answer=false, ANY
    # citation at all is suspicious since no document should have grounded
    # a real answer.
    unexpected_citation = bool(cited_docs - expected_docs) if expected_docs else bool(cited_docs)

    return {
        "case": case,
        "did_answer": did_answer,
        "citations": citations,
        "cited_doc_keys": cited_doc_keys,
        "unexpected_citation": unexpected_citation,
        "answer_text": answer_text,
    }


def print_report(results: list) -> None:
    for r in results:
        case = r["case"]
        print(f"\n[{case['id']}] {case['category']}")
        print(f"  Question:                   {case['question']}")
        print(f"  Should answer?               {case['should_answer']}")
        print(f"  Did answer?                  {r['did_answer']}")
        print(f"  Expected documents:          {case['expected_documents']}")
        print(f"  Returned citations:          {r['citations']}")
        print(f"  Cited from documents:        {r['cited_doc_keys']}")
        print(f"  Unexpected citation?         {r['unexpected_citation']}")
        print(f"  Answer text:                 {r['answer_text']}")
        print("  Manual groundedness result:  ____________  <- fill in by hand, see eval/groundedness_report.md")


def run_evaluation(use_fake: bool = False) -> list:
    data = load_cases()
    repo = make_scratch_repo()
    id_map = seed_documents(repo, data["documents"])
    provider = build_provider(use_fake)

    print(f"Provider: {type(provider).__name__}")
    print(f"Documents seeded: {len(id_map)}")
    print(f"Cases to run: {len(data['cases'])}")
    print("=" * 100)

    results = [run_case(case, repo, provider, id_map) for case in data["cases"]]
    print_report(results)
    return results


if __name__ == "__main__":
    run_evaluation(use_fake="--fake" in sys.argv)