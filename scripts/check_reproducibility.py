"""
Reproducibility check for /answer - runs the same question multiple times
against identical documents and settings, then reports separately whether
RETRIEVAL was stable (same chunk IDs + scores every run) and whether
GENERATION was stable (same answer + citations every run).

These are deliberately reported separately: retrieval (TF-IDF) is a
deterministic algorithm over a fixed corpus, so unless the underlying
data changes between runs, it should be identical every time. An LLM's
text output can vary between calls even given identical input, depending
on the provider/model's own sampling - that's a SEPARATE question from
whether retrieval found the same evidence, and this script is built to
never conflate the two.

Usage:
    python -m scripts.check_reproducibility            # real Ollama, 5 runs
    python -m scripts.check_reproducibility --fake     # FakeLLMProvider, quick smoke test
    python -m scripts.check_reproducibility --runs 10  # more runs
"""

import argparse
import os
import tempfile

from app.core.config import settings
from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.llm.ollama_provider import OllamaLLMProvider
from app.models import AnswerRequest
from app.services.answer_service import generate_answer
from app.services.chunking_service import chunk_text

QUESTION = "What is the laptop reimbursement limit?"
DOCUMENT_TEXT = (
    "IT Policy Document. Laptop reimbursement limit is $2000 USD. "
    "All equipment must be approved by IT manager before purchase."
)

# Harder scenario: mirrors case 4 from the groundedness eval (Task 17) -
# multiple documents give genuinely different numbers for a similar
# question. Included so this script can produce evidence on a case that
# actually failed before, not just an easy single-fact lookup.
CONFLICTING_QUESTION = "How many days does expense reimbursement take to process?"
CONFLICTING_DOCUMENTS = {
    "hr_policy.txt": "HR Policy. Expense reimbursement for approved business travel is processed within 5 working days.",
    "it_policy.txt": "IT Policy. Reimbursement for approved software is processed within 10 days.",
    "finance_policy.txt": "Finance Policy. Approval process takes 3-5 business days.",
}


def make_scratch_repo() -> SQLiteDocumentRepository:
    tmp_dir = tempfile.mkdtemp(prefix="repro_check_")
    db_path = os.path.join(tmp_dir, "repro.db")
    repo = SQLiteDocumentRepository(f"sqlite:///{db_path}")
    Base.metadata.create_all(repo.engine)
    return repo


def build_provider(use_fake: bool):
    if use_fake:
        return FakeLLMProvider(response="The laptop reimbursement limit is $2000 USD.")
    return OllamaLLMProvider(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        timeout=settings.llm_timeout_seconds,
    )


def run_once(repo, provider, question: str, run_number: int) -> dict:
    request = AnswerRequest(question=question, top_k=3, min_score=0.1, retrieval_mode="tfidf")
    response = generate_answer(request, repo, provider, request_id=f"repro-{run_number}")
    return {
        "run": run_number,
        "retrieved_chunk_ids": [c.chunk_id for c in response.retrieved_chunks],
        "retrieved_scores": [c.score for c in response.retrieved_chunks],
        "answer": response.answer,
        "citations": response.citations,
    }


def check_reproducibility(num_runs: int, use_fake: bool, scenario: str) -> None:
    repo = make_scratch_repo()
    if scenario == "conflicting":
        question = CONFLICTING_QUESTION
        for name, text in CONFLICTING_DOCUMENTS.items():
            repo.create_document_with_chunks(name, text, chunk_text)
    else:
        question = QUESTION
        repo.create_document_with_chunks("it_policy.txt", DOCUMENT_TEXT, chunk_text)
    provider = build_provider(use_fake)

    print(f"Scenario: {scenario}")
    print(f"Provider: {type(provider).__name__}")
    print(f"Question: {question!r}")
    print(f"Runs: {num_runs}")
    print("=" * 100)

    results = [run_once(repo, provider, question, i + 1) for i in range(num_runs)]

    for r in results:
        print(f"\n[run {r['run']}]")
        print(f"  Retrieved chunk IDs: {r['retrieved_chunk_ids']}")
        print(f"  Retrieved scores:    {r['retrieved_scores']}")
        print(f"  Citations:           {r['citations']}")
        print(f"  Answer:              {r['answer']}")

    first = results[0]

    # Retrieval stability: chunk IDs AND scores must match every run.
    # Scores matter too - same chunk IDs with a drifted score would still
    # be a real (if subtle) change, not stability.
    retrieval_stable = all(
        r["retrieved_chunk_ids"] == first["retrieved_chunk_ids"]
        and r["retrieved_scores"] == first["retrieved_scores"]
        for r in results
    )

    # Generation stability: answer text and citations must match every
    # run. Checked independently of retrieval - generation could vary
    # even when retrieval doesn't (non-deterministic model sampling on
    # identical input), and that's the exact distinction this script
    # exists to make visible.
    generation_stable = all(
        r["answer"] == first["answer"] and r["citations"] == first["citations"]
        for r in results
    )

    print("\n" + "=" * 100)
    print(f"Retrieval stable:  {'Yes' if retrieval_stable else 'No'}")
    print(f"Generation stable: {'Yes' if generation_stable else 'No'}")
    print("\nEvidence:")

    if retrieval_stable:
        print(
            f"  - Retrieved chunk IDs and scores were identical across all "
            f"{num_runs} runs: {first['retrieved_chunk_ids']} / {first['retrieved_scores']}"
        )
    else:
        unique_chunk_sets = {tuple(r["retrieved_chunk_ids"]) for r in results}
        unique_score_sets = {tuple(r["retrieved_scores"]) for r in results}
        print(f"  - Retrieved chunk IDs varied across runs: {unique_chunk_sets}")
        print(f"  - Retrieved scores varied across runs: {unique_score_sets}")

    if generation_stable:
        print(f"  - Generated answer and citations were identical across all {num_runs} runs.")
    else:
        unique_answers = {r["answer"] for r in results}
        print(
            f"  - Generated answer varied across runs "
            f"({len(unique_answers)} distinct versions seen)."
        )
        if retrieval_stable:
            print(
                "  - IMPORTANT: retrieval was stable while generation was not - this "
                "variation comes from the LLM's own generation, NOT from retrieval. "
                "Do not attribute this to a retrieval problem."
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check /answer reproducibility across repeated runs.")
    parser.add_argument("--runs", type=int, default=5, help="Number of repeated runs (default: 5)")
    parser.add_argument("--fake", action="store_true", help="Use FakeLLMProvider instead of real Ollama")
    parser.add_argument(
        "--scenario", choices=["simple", "conflicting"], default="simple",
        help="'simple': one doc, one clear fact. 'conflicting': 3 docs with genuinely "
             "different numbers for a similar question - mirrors Task 17's case 4.",
    )
    args = parser.parse_args()

    check_reproducibility(args.runs, args.fake, args.scenario)