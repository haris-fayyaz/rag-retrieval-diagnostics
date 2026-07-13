from fastapi import FastAPI, HTTPException
from app.models import DocumentCreate, DocumentResponse, AskRequest, AskResponse, HealthResponse

from app.services.document_store import DocumentStore
from app.services.chunking_service import chunk_text
from app.services.retrieval import get_retriever


app = FastAPI(title="RAG Retrieval Diagnostics")

# Initialize services
doc_store = DocumentStore()

@app.get("/")
def main_app():
    return "Hello From FastAPI"

@app.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/documents", response_model=DocumentResponse)
def add_document(doc: DocumentCreate):
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
    response = doc_store.add_document(doc.name, doc.text)
    
    # Chunk document
    chunks = chunk_text(doc.text, response.document_id, doc.name)
    doc_store.update_chunks(response.document_id, chunks)
    
    # Update chunk count
    response.chunk_count = len(chunks)
    return response

@app.get("/documents", response_model=list[DocumentResponse])
def list_documents():
    """List all stored documents."""
    return doc_store.list_documents()

@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    """
    Retrieve relevant chunks for a question.
    
    Args:
        request: Question, top_k, and optional document filters
    Returns:
        Top-k ranked chunks with scores
    """
    # Gather all chunks (or filtered by document_ids)
    all_chunks = []
    for doc_id, doc in doc_store.documents.items():
        if request.document_ids and doc_id not in request.document_ids:
            continue
        all_chunks.extend(doc["chunks"])
    
    if not all_chunks:
        raise HTTPException(status_code=404, detail="No chunks found")
    

    # Choose retrieval mode
    retriever = get_retriever(request.retrieval_mode)
    # Retrieve top-k
    retrieved = retriever.retrieve(request.question, all_chunks, request.top_k)
    
    # Filter by min_score
    filtered = [chunk for chunk in retrieved if chunk.score >= request.min_score]
    
    message = None
    if not filtered:
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