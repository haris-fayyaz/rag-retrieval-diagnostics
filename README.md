# RAG Retrieval Diagnostics

A FastAPI backend for testing and evaluating RAG (Retrieval-Augmented
Generation) retrieval quality, with SQLite persistence and a grounded
answer-generation layer on top.

## Features

- **Persistent storage** — SQLite via SQLAlchemy ORM, managed with Alembic migrations
- **Repository pattern** — API and services depend on a `DocumentRepository` protocol, never on SQL directly
- **Three retrieval modes** — TF-IDF (default), semantic (sentence-transformers), and hybrid (reciprocal rank fusion)
- **Two question-answering endpoints**:
  - `/ask` — retrieval debug endpoint, returns raw scored chunks
  - `/answer` — user-facing endpoint, returns a grounded natural-language answer with citations
- **LLM provider abstraction** — swappable backends behind an `LLMProvider` protocol
- **Resilience** — configurable timeout, limited automatic retries on transient LLM failures only
- **Observability** — request tracing (`request_id`) and per-stage timing on every `/answer` call, structured JSON logs
- **Retrieval evaluation** — automated script scoring retrieval quality against a labeled question set
- **Groundedness & prompt-injection evaluation** — manual evaluation harness against a real LLM, checking whether answers stay grounded in retrieved context and resist instructions hidden inside documents
- **Answer audit trail** — every `/answer` call (success, no-context, or provider failure) is persisted to `answer_runs` and retrievable via `GET /answer-runs/{request_id}`, without changing `/answer`'s own response behavior
- **CI** — lint, tests, migration validation, and retrieval evaluation on every push
## Tech Stack

Python 3.12+ · FastAPI · SQLAlchemy 2.x · Alembic · scikit-learn (TF-IDF) · sentence-transformers (semantic) · pytest · ruff

## Setup

```bash
git clone https://github.com/haris-fayyaz/rag-retrieval-diagnostics.git
cd rag-retrieval-diagnostics
pip install -r requirements.txt
```

### Database

The app uses a SQLite file at `data/app.db` (gitignored, disposable).
Initialize/migrate it before first run:

```bash
alembic upgrade head
```

Delete `data/app.db` any time and rerun the command above to reset.

### Environment configuration

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `fake` | `fake` (deterministic, no network — used in tests/CI) or `ollama` (real local model) |
| `LLM_MODEL` | `qwen3:1.7b` | Model name, used only when `LLM_PROVIDER=ollama` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL, used only when `LLM_PROVIDER=ollama` |
| `LLM_TIMEOUT_SECONDS` | `30` | Max time to wait for a single provider call before it's treated as a timeout (retryable) |
| `LLM_MAX_RETRIES` | `1` | Additional attempts after the first on a *temporary* failure (timeout, connection error). Never retries validation errors, no-context, or permanent failures. Total attempts = 1 + this value, always bounded — never retries indefinitely |
| `LLM_API_KEY` | *(unused)* | Reserved for a future hosted API provider |
| `CHUNK_SIZE` | `800` | Max characters per chunk. Must be > 0 |
| `CHUNK_OVERLAP` | `100` | Characters of trailing context carried into the next chunk. Must be >= 0 and < `CHUNK_SIZE` |

**Note:** these are plain `os.environ` reads — the app does not auto-load
`.env`. Export the variables in your shell before starting the server if
you want anything other than the fake provider:

```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=qwen3:1.7b
export OLLAMA_BASE_URL=http://localhost:11434
```

### Manual testing with a real model (Ollama)

Automated tests never call Ollama - only `FakeLLMProvider` runs in CI.
To try a real model locally:

1. Install [Ollama](https://ollama.com/download) and pull the model:
```bash
ollama run qwen3:1.7b
```
(first run downloads the model; type `/bye` to exit the chat prompt - the server keeps running in the background)

2. Confirm the server is up:
```bash
curl http://localhost:11434/api/tags
```

3. Export the provider config in the same shell you'll run uvicorn from:
```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=qwen3:1.7b
export OLLAMA_BASE_URL=http://localhost:11434
export LLM_TIMEOUT_SECONDS=30
export LLM_MAX_RETRIES=1
```

4. Start the app and test via Swagger (`http://localhost:8000/docs`) or curl:
```bash
uvicorn app.main:app --reload
```
POST a document via `/documents`, then POST a question to `/answer` -
the `answer` field will now be real generated text (not the fake canned
response), and `metadata.provider` will read `"ollama"`.

## Running the Backend

```bash
uvicorn app.main:app --reload
```

Interactive API docs: `http://localhost:8000/docs`

## Observability

Every `/answer` request logs structured JSON lines to stdout
(`app/core/logging.py`), correlated by `request_id`:

- `answer_request_started`
- `retrieval_completed`
- `no_context_found` (only on the no-context path)
- `llm_attempt_started` (once per attempt, including retries)
- `provider_failed` (on any provider error, tagged `retryable: true/false`)
- `retry_triggered` (only when another attempt is about to happen)
- `answer_completed`

Example line:
```json
{"event": "retrieval_completed", "level": "INFO", "request_id": "4ea9...", "retrieval_mode": "tfidf", "retrieved_chunk_count": 1, "retrieval_ms": 12.4}
```

**Never logged:** API keys, full prompts, full question text, or full
document content. Log fields are limited to IDs, counts, modes, and
timings — enforced by `log_event()`'s explicit keyword-only signature,
which doesn't accept an arbitrary object that might contain sensitive
content by accident.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Health check |
| `POST /documents` | Add a document (chunked and persisted atomically) |
| `GET /documents` | List stored documents |
| `POST /documents/{document_id}/reindex` | Re-chunk a document's saved original text with the current `CHUNK_SIZE`/`CHUNK_OVERLAP`, replacing its chunks in one transaction |
| `POST /ask` | Retrieval debug — returns raw scored chunks, no generation |
| `POST /answer` | Grounded question answering — returns a generated answer with citations |
| `GET /answer-runs/{request_id}` | Fetch the stored audit record for a past `/answer` call — question, retrieved chunks, answer, status, timing. 404 if unknown |

### `/ask` vs `/answer`

`/ask` is for inspecting retrieval behavior directly — it returns the
scored chunks and nothing else. `/answer` builds on the same retrieval
step, then grounds a prompt in only the retrieved chunks, calls an LLM,
and returns a natural-language answer plus the chunk IDs it's grounded
in. `/ask` never calls an LLM; `/answer` never returns raw chunk text
previews, only source references.

### `POST /answer` example

Request:
```json
{
  "question": "What is the laptop reimbursement limit?",
  "document_ids": ["1"],
  "retrieval_mode": "tfidf",
  "top_k": 3,
  "min_score": 0.10
}
```

Response:
```json
{
  "request_id": "4ea9c1b2-6f3a-4e9d-9c2a-8f1e2d3c4b5a",
  "question": "What is the laptop reimbursement limit?",
  "answer": "Employees may claim up to $800 for an approved laptop purchase.",
  "citations": ["1_chunk_0"],
  "retrieved_chunks": [
    {
      "chunk_id": "1_chunk_0",
      "document_id": "1",
      "document_name": "it_policy.txt",
      "score": 0.82
    }
  ],
  "message": null,
  "metadata": {
    "retrieval_ms": 12.4,
    "generation_ms": 820.7,
    "total_ms": 835.1,
    "retrieved_chunk_count": 1,
    "retrieval_mode": "tfidf",
    "provider": "ollama"
  }
}
```

`request_id` is a fresh UUID generated per request, present in every
response - success, validation error, or provider failure - so a single
ID can be used to correlate a client-reported issue with server logs.

`metadata` reports execution timing separately for retrieval and
generation, plus which mode/provider actually ran. `generation_ms` is
`null` whenever the LLM was never called (no-context requests never
reach the LLM step at all).

### Grounding and no-context behavior

- Only chunks returned by retrieval are sent to the LLM — never the full document store.
- Each chunk is tagged with its ID in the prompt (`[1_chunk_0]`), and the model is instructed to cite by ID and to say so if the context doesn't contain the answer.
- Retrieved chunks are wrapped in explicit `<untrusted_context>` tags (built by `app/services/prompt_builder.py`), with instructions telling the model that text inside the tags is data to read, never a command to obey. This defends against prompt injection - a malicious or compromised document containing text like "ignore previous instructions" is still just data to the model, not a command.
- `citations` is computed from the chunks actually retrieved, not parsed from the model's text — this keeps citations reliable regardless of how the model phrases its answer.
- If no chunk clears `min_score`, the LLM is never called. The response returns `answer: null` with an explanatory `message`:
```json
{
  "question": "What is the cryptocurrency payment policy?",
  "answer": null,
  "citations": [],
  "retrieved_chunks": [],
  "message": "No relevant information was found in the selected documents."
}
```

### Error handling (`/answer`)

| Condition | Response |
|---|---|
| Empty question | `400`, `{"request_id": ..., "error": ...}` |
| Unsupported `retrieval_mode` | `400`, `{"request_id": ..., "error": ...}` |
| Invalid/unknown `document_ids` | `200` with no-context response (not an error — same as no matching chunks) |
| No chunks above `min_score` | `200` with no-context response |
| LLM provider failure (after retries exhausted) | `502`, `{"request_id": ..., "error": ...}` — controlled error, no stack trace |

Every error response includes the same `request_id` a success response
would have had, so it can be matched to the corresponding server logs.

### Retries and timeouts

Only genuinely transient LLM failures are retried:

| Failure | Retried? | Why |
|---|---|---|
| Timeout (`LLM_TIMEOUT_SECONDS` exceeded) | Yes | May just need another attempt (e.g. model still warming up) |
| Connection refused / provider unreachable | Yes | Provider may become reachable again shortly |
| 5xx from provider | Yes | Server-side issue on the provider's end, may be transient |
| 4xx from provider (bad model, malformed request) | **No** | Retrying resends the identical bad request — will fail the same way every time |
| Empty response from provider | **No** | A 200 OK with no text isn't a network problem, retrying won't change the outcome |
| Empty question / unsupported retrieval mode | **No** | Validation errors, never reach the provider at all |
| No chunks found (no-context) | **No** | The LLM is never called in the first place |

Retries are capped by `LLM_MAX_RETRIES` and can never loop indefinitely —
the retry count is fixed before the first attempt is made, not decided
dynamically. Once attempts are exhausted, the endpoint returns `502`.

## Answer Audit Trail

Every `/answer` call is persisted to the `answer_runs` table — regardless
of outcome (success, no relevant context, or provider failure) — so past
executions can be inspected later without needing to reproduce them.

Stored per run: `request_id`, `question`, `answer` (nullable), `status`
(`success`/`no_context`/`provider_error`), `retrieval_mode`, `top_k`,
`min_score`, `provider`, `model`, `retrieved_chunk_ids`, `citations`,
and `retrieval_ms`/`generation_ms`/`total_ms` timing.

**Not stored:** the full prompt, API keys, or full document content —
only IDs, the question, the final answer, and metadata.

**The write is best-effort and defensive** (`_record_audit` in
`answer_service.py`): if persisting the audit record itself fails (e.g. a
locked DB file), the failure is logged but never raised — a broken audit
write can never turn a successful `/answer` call into an error response.
This is what "audit persistence should not change the existing API
response behavior" means in practice.

Fetch a past run:
```bash
curl http://localhost:8000/answer-runs/4ea9c1b2-6f3a-4e9d-9c2a-8f1e2d3c4b5a
```
Returns `404` if `request_id` was never recorded.

### Reproducibility check

```bash
python -m scripts.check_reproducibility            # simple single-fact question, real Ollama
python -m scripts.check_reproducibility --fake      # smoke test with FakeLLMProvider
python -m scripts.check_reproducibility --scenario conflicting   # harder: conflicting sources
```

Runs the same question 5x against identical documents and settings, then
reports **retrieval stability** (chunk IDs + scores) and **generation
stability** (answer text + citations) as two separate Yes/No verdicts —
so answer variation is never misattributed to retrieval unless the chunk
IDs or scores actually changed.

Findings: `eval/reproducibility_findings.md`. Headline result: retrieval
is fully deterministic (identical chunk IDs/scores to exact float
precision across every run tested); generation is not — on a simple
question this only affects wording, but on a conflicting-source question
the model gave a different final number across different runs from the
exact same retrieved evidence.

## Testing

```bash
pytest
```

Automated tests use `FakeLLMProvider` — no network calls, no API key,
and no Ollama dependency. CI never requires a real model. Semantic and
hybrid retrieval tests need Hugging Face access to download an embedding
model, so they're marked `@pytest.mark.integration` and excluded from
the default run (see `pytest.ini`). Run them explicitly when you have
network access:

```bash
pytest -m integration
```

Coverage includes: document/chunk persistence, transactional
create-with-chunks (no orphaned documents on failure), retrieval over
persisted data, `/answer` grounding and citations, no-context rejection,
retrieval selectivity across `top_k`/`min_score`, provider-failure
handling, request tracing, timing metadata, retry/timeout behavior
(`tests/test_resilience.py`), chunking correctness (no truncation,
overlap, config validation — `tests/test_chunking.py`), re-indexing
(`tests/test_reindex.py`), and the audit trail — all 3 outcomes recorded,
fetchable by `request_id`, unknown IDs return 404 (`tests/test_audit.py`).

## Retrieval Evaluation

```bash
python -m scripts.evaluate_retrieval --mode tfidf --min-score 0.10 --top-k 3
```

Scores retrieval quality (top-1 accuracy, recall@k) against a labeled
question set in `eval/eval_questions.json`. Supports `tfidf`, `semantic`,
and `hybrid` modes. See `eval/retrieval_comparison.md` for prior findings.

## Groundedness and Prompt-Injection Evaluation

Checks whether `/answer` stays grounded in retrieved context, refuses
when it shouldn't answer, and resists instructions hidden inside
retrieved documents (prompt injection, prompt-leak attempts).

```bash
# Smoke test - proves the harness itself runs, NOT a real groundedness result
python -m scripts.evaluate_answers --fake

# Real evaluation - requires Ollama running locally (see "Manual testing
# with a real model" above)
python -m scripts.evaluate_answers
```

The script seeds `eval/answer_eval_cases.json` (11 cases covering direct
lookups, multi-chunk answers, unsupported questions, conflicting sources,
prompt injection, and prompt-leak attempts) into a scratch SQLite DB, runs
each through the real `/answer` pipeline, and prints a report table for
manual review. **No LLM is used as a judge** - every result is read and
classified by hand, per the project's evaluation standard.

Full results, per-case classification, and root-cause analysis (retrieval
vs. generation failures) are in `eval/groundedness_report.md`. Headline
finding: the hardened prompt (`app/services/prompt_builder.py`) reduces
prompt-injection risk but does not eliminate it - one of two tested
injection attempts still succeeded. See the report for details.

## Architecture Notes

- **Repository pattern**: `app/database/repositories/interface.py` defines the `DocumentRepository` protocol; `sqlite_repository.py` is the only implementation. The API and services depend solely on the protocol.
- **LLM provider pattern**: `app/llm/provider.py` defines the `LLMProvider` protocol. `FakeLLMProvider` (tests/CI) and `OllamaLLMProvider` (local, real) both implement it; `answer_service.py` depends only on the interface.
- **Prompt hardening**: `app/services/prompt_builder.py` is the single place that builds the `/answer` prompt, kept separate from `answer_service.py` so its safety properties (untrusted-context framing, groundedness rules, refusal permission) can be unit-tested in isolation (`tests/test_prompt_builder.py`) without a DB or a real LLM.
- **Exception hierarchy**: `app/llm/exceptions.py` distinguishes retryable (`LLMTemporaryError`, `LLMTimeoutError`) from non-retryable (`LLMPermanentError`) provider failures - this is what lets retry logic be type-driven instead of string-matching error messages.
- **Config**: `app/core/config.py` centralizes all environment variable reads into one `Settings` object, instead of scattered `os.environ.get()` calls.
- **Logging**: `app/core/logging.py` provides structured JSON logging via a `log_event()` helper with an explicit keyword-only signature - callers can't accidentally log a whole object that might contain sensitive content.
- **Migrations**: Alembic manages schema changes under `alembic/versions/`. Never edit the schema by hand — add a new migration.
- **Audit trail**: `answer_runs` (via `AnswerRunORM`) has no foreign key to documents/chunks by design - a record must remain readable even after the source document is deleted or re-indexed. Writing it is best-effort (`_record_audit` in `answer_service.py`) - failures are logged, never raised, so audit persistence can't affect `/answer`'s actual response.