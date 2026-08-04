"""
Shared state for the bounded document assistant graph.

This is NOT a chat history. It is one execution's worth of data,
built once by the endpoint and threaded through route -> execute ->
generate. Every node reads a subset of this and returns a partial
dict of the fields it changed; LangGraph merges those into the
full state before calling the next node.
"""

from typing import List, Optional, TypedDict


class AgentState(TypedDict):
    # --- Set once by the endpoint, never mutated by nodes ---
    request_id: str
    query: str
    document_ids: Optional[List[str]]
    top_k: int
    min_score: float

    # --- Written by the routing node ---
    selected_tool: Optional[str]  # "search_documents" | "list_documents" | "get_answer_run" | None

    # --- Written by the tool-execution node ---
    tool_result: Optional[dict]

    # --- Written by the response-generation node ---
    answer: Optional[str]
    citations: List[str]  # chunk_ids, sourced only from tool_result - never model text

    # --- Written by every node, checked at each step ---
    status: str  # "success" | "no_context" | "refused" | "tool_error"
    step_count: int
    error: Optional[str]