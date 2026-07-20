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
- **Retrieval evaluation** — automated script scoring retrieval quality against a labeled question set
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
| `LLM_API_KEY` | *(unused)* | Reserved for a future hosted API provider |

**Note:** these are plain `os.environ` reads — the app does not auto-load
`.env`. Export the variables in your shell before starting the server if
you want anything other than the fake provider:

```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=qwen3:1.7b
export OLLAMA_BASE_URL=http://localhost:11434
```

For real local answers, install [Ollama](https://ollama.com/download) and pull the model:

```bash
ollama run qwen3:1.7b
```

## Running the Backend

```bash
uvicorn app.main:app --reload
```

Interactive API docs: `http://localhost:8000/docs`

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Health check |
| `POST /documents` | Add a document (chunked and persisted atomically) |
| `GET /documents` | List stored documents |
| `POST /ask` | Retrieval debug — returns raw scored chunks, no generation |
| `POST /answer` | Grounded question answering — returns a generated answer with citations |

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
  "message": null
}
```

### Grounding and no-context behavior

- Only chunks returned by retrieval are sent to the LLM — never the full document store.
- Each chunk is tagged with its ID in the prompt (`[1_chunk_0]`), and the model is instructed to cite by ID and to say so if the context doesn't contain the answer.
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
| Empty question | `400` |
| Unsupported `retrieval_mode` | `400` |
| Invalid/unknown `document_ids` | `200` with no-context response (not an error — same as no matching chunks) |
| No chunks above `min_score` | `200` with no-context response |
| LLM provider failure | `502`, controlled error detail (no stack trace) |

## Testing

```bash
pytest
```

Automated tests use `FakeLLMProvider` — no network calls, no API key,
and no Ollama dependency. CI never requires a real model.

Coverage includes: document/chunk persistence, transactional
create-with-chunks (no orphaned documents on failure), retrieval over
persisted data, `/answer` grounding and citations, no-context rejection,
retrieval selectivity across `top_k`/`min_score`, and provider-failure
handling.

## Retrieval Evaluation

```bash
python -m scripts.evaluate_retrieval --mode tfidf --min-score 0.10 --top-k 3
```

Scores retrieval quality (top-1 accuracy, recall@k) against a labeled
question set in `eval/eval_questions.json`. Supports `tfidf`, `semantic`,
and `hybrid` modes. See `eval/retrieval_comparison.md` for prior findings.

## Architecture Notes

- **Repository pattern**: `app/database/repositories/interface.py` defines the `DocumentRepository` protocol; `sqlite_repository.py` is the only implementation. The API and services depend solely on the protocol.
- **LLM provider pattern**: `app/llm/provider.py` defines the `LLMProvider` protocol. `FakeLLMProvider` (tests/CI) and `OllamaLLMProvider` (local, real) both implement it; `answer_service.py` depends only on the interface.
- **Migrations**: Alembic manages schema changes under `alembic/versions/`. Never edit the schema by hand — add a new migration.