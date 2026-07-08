from typing import Dict, List, Optional
from app.models import DocumentResponse, DocData

class DocumentStore:
    """In-memory document storage."""
    
    def __init__(self):
        self.documents: Dict[str, DocData] = {}
        self.doc_counter = 0
    
    def add_document(self, name: str, text: str) -> DocumentResponse:
        """Store document and return metadata."""
        if not text.strip():
            raise ValueError("Document text cannot be empty")
        
        doc_id = f"doc_{self.doc_counter}"
        self.doc_counter += 1
        
        self.documents[doc_id] = {
            "name": name,
            "text": text,
            "chunks": []  # Will be populated by chunking service
        }
        
        return DocumentResponse(
            document_id=doc_id,
            name=name,
            chunk_count=0
        )
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Retrieve document by ID."""
        return self.documents.get(doc_id)
    
    def list_documents(self) -> List[DocumentResponse]:
        """List all documents."""
        return [
            DocumentResponse(
                document_id=doc_id,
                name=doc["name"],
                chunk_count=len(doc["chunks"])
            )
            for doc_id, doc in self.documents.items()
        ]
    
    def update_chunks(self, doc_id: str, chunks: List) -> None:
        """Store chunks for a document."""
        if doc_id in self.documents:
            self.documents[doc_id]["chunks"] = chunks