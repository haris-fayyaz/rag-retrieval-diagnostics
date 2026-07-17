from app.services.retrieval.interface import Retriever
from app.services.retrieval.tfidf import TFIDFRetriever
from app.services.retrieval.semantic import SemanticRetrievalService
from app.services.retrieval.hybrid import HybridRetriever

def get_retriever(mode: str) -> Retriever:
    """Get retriever by mode.

    Builds only the requested retriever, not all of them. Previously this
    constructed TFIDFRetriever, SemanticRetrievalService, AND
    HybridRetriever on every call regardless of `mode` - meaning a plain
    "tfidf" request still loaded the sentence-transformer model (slow, and
    fails outright with no network). Each branch now only pays for what
    it needs.
    """
    if mode == "tfidf":
        return TFIDFRetriever()
    if mode == "semantic":
        return SemanticRetrievalService()
    if mode == "hybrid":
        return HybridRetriever()

    raise ValueError(f"Unknown retrieval mode: {mode}. Use 'tfidf', 'semantic', or 'hybrid'.")