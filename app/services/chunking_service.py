from typing import List
from app.models import Chunk

def chunk_text(text: str, document_id: str, document_name: str, chunk_size: int = 200) -> List[Chunk]:
    """
    Split text into chunks by paragraphs.
    
    Args:
        text: Document text to chunk
        document_id: ID of the source document
        document_name: Name of the source document
        chunk_size: Target size per chunk (characters)
    
    Returns:
        List of Chunk objects with metadata
    """
    if not text.strip():
        return []
    
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    chunk_index = 0
    
    for para in paragraphs:
        # Combine paragraphs until we exceed chunk_size
        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += para + "\n\n"
        else:
            # Save current chunk and start new one
            if current_chunk.strip():
                chunk_id = f"{document_id}_chunk_{chunk_index}"
                chunks.append(Chunk(
                    document_id=document_id,
                    document_name=document_name,
                    chunk_id=chunk_id,
                    score=0.0,
                    text_preview=current_chunk.strip()[:200]  # First 200 chars for preview
                ))
                chunk_index += 1
            current_chunk = para + "\n\n"
    
    # Save final chunk
    if current_chunk.strip():
        chunk_id = f"{document_id}_chunk_{chunk_index}"
        chunks.append(Chunk(
            document_id=document_id,
            document_name=document_name,
            chunk_id=chunk_id,
            score=0.0,
            text_preview=current_chunk.strip()[:200]
        ))
    
    return chunks