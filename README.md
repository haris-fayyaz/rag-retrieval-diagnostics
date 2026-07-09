# RAG Retrieval Diagnostics

A lightweight, in-memory RAG (Retrieval-Augmented Generation) backend for testing and evaluating retrieval quality.

## Features

- **FastAPI Backend**: 4 endpoints for document management and retrieval
- **TF-IDF Retrieval**: Cosine similarity-based document ranking (no embeddings yet)
- **In-Memory Storage**: Dictionary-based document and chunk storage
- **Paragraph Chunking**: Automatic text splitting with configurable chunk size (default: 200 characters)
- **Retrieval Evaluation**: Automated evaluation script to measure retrieval quality
- **CI/CD Pipeline**: GitHub Actions for linting (ruff) and testing (pytest)

## Tech Stack

- Python 3.14
- FastAPI
- Pydantic
- scikit-learn (TF-IDF)
- pytest
- ruff (linting)

## Setup

```bash
# Clone and install
git clone https://github.com/haris-fayyaz/rag-retrieval-diagnostics.git
cd rag-retrieval-diagnostics
pip install -r requirements.txt
```

## Running the Backend

```bash
# Start the server (runs on http://localhost:8000)
python -m uvicorn app.main:app --reload
```

**Available Endpoints:**

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /documents` - Add a new document (returns document_id and chunk_count)
- `GET /documents` - List all stored documents
- `POST /ask` - Retrieve relevant chunks for a question

Example request:

```json
POST /ask
{
  "question": "What is the laptop reimbursement limit?",
  "top_k": 3,
  "document_ids": null
}
```

## Testing

Run the test suite:

```bash
pytest
```

Current status: **4 tests passing** ✓

## Retrieval Evaluation

Measure retrieval quality automatically with the evaluation script:

```bash
python scripts/evaluate_retrieval.py
```

### What the Evaluation Script Does

1. **Loads sample documents**: 3 policy documents (HR, IT, Finance) from `eval/sample_documents.json`
2. **Loads evaluation questions**: 8 diverse questions from `eval/eval_questions.json`
   - 3 single-document questions (clear answers)
   - 1 multi-document question (requires cross-doc reasoning)
   - 2 unanswerable/vague questions (should return null)
   - 2 misleading questions (edge cases)
3. **Runs retrieval**: Queries the system with each question
4. **Compares results**: Matches top-retrieved chunk's document against expected document
5. **Reports accuracy**: Shows pass/fail per question and overall accuracy metric

### Example Output

```
RETRIEVAL EVALUATION RESULTS
========================================================================================================================
Question                                      Expected        Top Result      Score      Pass
========================================================================================================================
How much annual leave are employees entitl... hr_policy       hr_policy       0.4862     ✓
What is the laptop reimbursement limit?       it_policy       it_policy       0.1877     ✓
...

========================================
SUMMARY METRICS
========================================
Total questions:  8
Passed:           4
Failed:           4
Accuracy:         50.0%
========================================
```

## Project Structure

```
rag-retrieval-diagnostics/
├── app/
│   ├── main.py                    # FastAPI application & endpoints
│   ├── models.py                  # Pydantic schemas
│   └── services/
│       ├── chunking_service.py    # Text splitting (paragraph-based)
│       ├── document_store.py      # In-memory document storage
│       └── retrieval_service.py   # TF-IDF ranking
├── tests/
│   ├── test_chunking.py
│   └── test_retrieval.py
├── eval/
│   ├── sample_documents.json      # 3 sample policy documents
│   └── eval_questions.json        # 8 evaluation questions
├── scripts/
│   └── evaluate_retrieval.py      # Retrieval quality evaluation script
├── .github/
│   └── workflows/ci.yml           # GitHub Actions CI pipeline
├── requirements.txt
└── README.md
```

## Key Configuration

- **Chunk Size**: 200 characters (configured in `chunking_service.py`)
- **Chunking Strategy**: Paragraph-based (splits on `\n\n`)
- **Retrieval Method**: TF-IDF + cosine similarity
- **Default Top-K**: 3 results

## Next Steps

This is a **baseline implementation**. Future improvements include:

- [ ] Token-based chunking (instead of character-based)
- [ ] Embedding-based retrieval (instead of TF-IDF)
- [ ] Persistent database (instead of in-memory)
- [ ] LLM integration for answer generation
- [ ] Advanced evaluation metrics (NDCG, MRR, F1)
- [ ] Reranking component

## CI/CD Pipeline

The project includes GitHub Actions workflow (`ci.yml`):

- Runs on every push/PR to `develop` and `main`
- Linting with ruff
- Tests with pytest
- Main branch is protected (PR-only merges)

## Notes

- No LLM integration yet (retrieval only)
- No embeddings or vector databases yet (TF-IDF baseline)
- In-memory storage (data lost on restart)
- For educational and diagnostic purposes

## License

MIT
