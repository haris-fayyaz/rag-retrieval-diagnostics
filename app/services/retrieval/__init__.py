from app.services.retrieval.retrieval_interface import Retriever
from app.services.retrieval.tfidf_retrieval_service import RetrievalService
from app.services.retrieval.semantic_retrieval_service import SemanticRetrievalService
from app.services.retrieval.hybrid import HybridRetriever

def get_retriever(mode: str) -> Retriever:
    """Get retriever by mode."""
    retrievers = {
        "tfidf": RetrievalService(),
        "semantic": SemanticRetrievalService(),
        "hybrid": HybridRetriever()
    }
    
    if mode not in retrievers:
        raise ValueError(f"Unknown retrieval mode: {mode}. Use 'tfidf', 'semantic', or 'hybrid'.")
    
    return retrievers[mode]