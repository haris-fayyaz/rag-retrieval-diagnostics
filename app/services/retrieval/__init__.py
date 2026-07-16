from app.services.retrieval.interface import Retriever
from app.services.retrieval.tfidf import TFIDFRetriever
from app.services.retrieval.semantic import SemanticRetrievalService
from app.services.retrieval.hybrid import HybridRetriever

def get_retriever(mode: str) -> Retriever:
    """Get retriever by mode."""
    retrievers = {
        "tfidf": TFIDFRetriever(),
        "semantic": SemanticRetrievalService(),
        "hybrid": HybridRetriever()
    }
    
    if mode not in retrievers:
        raise ValueError(f"Unknown retrieval mode: {mode}. Use 'tfidf', 'semantic', or 'hybrid'.")
    
    return retrievers[mode]