# RAG Retrieval Diagnostics

A lightweight backend for document chunking and semantic retrieval using TF-IDF.

## Features

* Add and store documents in memory
* Split documents into chunks
* Retrieve the most relevant chunks using TF-IDF similarity
* Filter retrieval by document ID
* Interactive API documentation through Swagger UI
* Automated tests with Pytest

## Setup

Create and activate a virtual environment:

Requires Python 3.14+

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the API

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

Once the server is running, open the Swagger UI:

`http://localhost:8000/docs`


## Python Version

- This project requires **Python 3.14** for dependency compatibility.
- CI pipeline tests on Python 3.14 via GitHub Actions.

## CI/CD

Automated checks run on every push to `develop` and pull request to `main`:
- Lint: `ruff check .`
- Tests: `pytest`

See workflow: `.github/workflows/ci.yml`

## API Endpoints

### Health Check

**GET** `/health`

Response:

```json
{
  "status": "ok"
}
```

### Add a Document

**POST** `/documents`

Request body:

```json
{
  "name": "hr_policy.txt",
  "text": "Long document text goes here."
}
```

Response:

```json
{
  "document_id": "doc_0",
  "name": "hr_policy.txt",
  "chunk_count": 3
}
```

### List Documents

**GET** `/documents`

Returns all documents currently stored in memory.

### Retrieve Relevant Chunks

**POST** `/ask`

Request body:

```json
{
  "question": "What is the laptop reimbursement policy?",
  "top_k": 3,
  "document_ids": ["doc_0"]
}
```

Response:

Returns the top-k document chunks ranked by TF-IDF similarity to the question.

## Run Tests

Run the test suite with:

```bash
pytest tests/ -v
```

## Evaluation

Run retrieval evaluation on sample questions:

```bash
python scripts/evaluate_retrieval.py
```

This loads 3 sample documents (HR, IT, Finance policies), runs 8 test questions, and measures retrieval accuracy. Tracks whether the retrieval system returns the expected document for each question.

## Current Limitations

The following features are not included yet:

* LLM integration
* Docker support
* Persistent database storage
* LangChain integration
* Frontend interface
* Advanced token-based chunking

> Note: Documents are currently stored in memory, so all data is lost when the server restarts.