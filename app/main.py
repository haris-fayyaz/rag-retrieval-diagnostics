from fastapi import Depends, FastAPI, HTTPException
from app.models import DocumentCreate, DocumentResponse, AskRequest, AskResponse, HealthResponse

from app.database.repositories.interface import DocumentRepository
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.services.chunking_service import chunk_text
from app.services.retrieval import get_retriever


app = FastAPI(title="RAG Retrieval Diagnostics")

# Single repository instance backing the running app (points at the
# SQLite file resolved by app.db.session, or DATABASE_URL if set).
_repository = SQLiteDocumentRepository()


def get_repository() -> DocumentRepository:
    """FastAPI dependency - overridden in tests to point at a temp DB."""
    return _repository

@app.get("/")
def main_app():
    return "Hello From FastAPI"

@app.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/documents", response_model=DocumentResponse)
def add_document(doc: DocumentCreate, repo: DocumentRepository = Depends(get_repository)):
    """
    Add a new document and chunk it.
    
    Args:
        doc: Document with name and text
    
    Returns:
        Document metadata with chunk count
    """
    if not doc.text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty")

    # Store document
    response = repo.add_document(doc.name, doc.text)

    # Chunk document and persist the chunks
    chunks = chunk_text(doc.text, response.document_id, doc.name)
    repo.save_chunks(response.document_id, chunks)

    # Update chunk count
    response.chunk_count = len(chunks)
    return response

@app.get("/documents", response_model=list[DocumentResponse])
def list_documents(repo: DocumentRepository = Depends(get_repository)):
    """List all stored documents."""
    return repo.list_documents()

@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, repo: DocumentRepository = Depends(get_repository)):
    """
    Retrieve relevant chunks for a question.
    
    Args:
        request: Question, top_k, and optional document filters
    Returns:
        Top-k ranked chunks with scores
    """
    # Gather persisted chunks (or filtered by document_ids)
    all_chunks = repo.get_chunks(request.document_ids)

    if not all_chunks:
        raise HTTPException(status_code=404, detail="No chunks found")
    

    # Choose retrieval mode and retrieve with threshold
    retriever = get_retriever(request.retrieval_mode)
    retrieved = retriever.retrieve(request.question, all_chunks, request.top_k, request.min_score)

    message = None
    if not retrieved:
        message = "No relevant chunks found above confidence threshold."

    return AskResponse(
        question=request.question,
        top_k=request.top_k,
        retrieved_chunks=retrieved,
        message=message
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)