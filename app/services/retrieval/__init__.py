from app.services.retrieval.retrieval_interface import Retriever
from app.services.retrieval.tfidf_retrieval_service import TFIDF
from app.services.retrieval.semantic_retrieval_service import SemanticRetrievalService

def get_retriever(mode: str) -> Retriever:
    retrievers = {
        "tfidf": TFIDF(),
        "semantic": SemanticRetrievalService()
    }
    if mode not in retrievers:
        raise ValueError(f"Unknown mode: {mode}")
    return retrievers[mode]