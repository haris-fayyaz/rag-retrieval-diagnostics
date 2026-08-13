"""
Bounded LangGraph for the document assistant.

START -> route -> (execute_tool -> generate) | generate -> END
Refused requests skip execute_tool. Max 3 steps, no loops, no retries,
one tool per request - guaranteed by the graph shape, not a counter.
"""

import re

from langgraph.graph import END, START, StateGraph

from app.agent.router import QueryRouter
from app.agent.state import AgentState
from app.agent.tools import ToolError, _citations_from_chunk_ids, get_answer_run, list_documents, search_documents
from app.core.logging import get_logger, log_event

logger = get_logger()

# AgentQueryRequest has one free-text field ("query"), reused for both
# document questions and "look up this request_id". Pulls an ID-like
# token out of the text; falls back to the raw query if none found
# (covers non-UUID test IDs like "test-001").
_ID_PATTERN = re.compile(r"[\w-]{6,}")


def _extract_request_id(query: str) -> str:
    matches = _ID_PATTERN.findall(query)
    return matches[-1] if matches else query.strip()


def build_document_assistant_graph(repo, retriever, router: QueryRouter):
    """repo/retriever/router are injected once at import time (see
    main.py) - never rebuilt per request."""

    def route_node(state: AgentState) -> dict:
        step = state["step_count"] + 1
        tool = router.route(state["query"])
        if tool is None:
            log_event(logger, "agent_refused", request_id=state["request_id"])
            return {"selected_tool": None, "status": "refused", "step_count": step}
        return {"selected_tool": tool, "status": "success", "step_count": step}

    def execute_tool_node(state: AgentState) -> dict:
        step = state["step_count"] + 1
        tool = state["selected_tool"]
        try:
            if tool == "search_documents":
                result = search_documents(
                    query=state["query"], document_ids=state["document_ids"],
                    top_k=state["top_k"], min_score=state["min_score"],
                    repo=repo, retriever=retriever,
                )
            elif tool == "list_documents":
                result = list_documents(repo=repo)
            else:  # get_answer_run
                result = get_answer_run(request_id=_extract_request_id(state["query"]), repo=repo)
        except ToolError as exc:
            log_event(logger, "agent_tool_failed", tool=tool, error=str(exc))
            return {"tool_result": None, "error": str(exc), "status": "tool_error", "step_count": step}
        return {"tool_result": result, "step_count": step}

    def generate_response_node(state: AgentState) -> dict:
        step = state["step_count"] + 1
        status = state["status"]

        if status == "refused":
            return {
                "answer": "I can only search documents, list documents, or look up a past answer by request ID.",
                "citations": [], "step_count": step,
            }
        if status == "tool_error":
            return {"answer": f"Something went wrong: {state['error']}", "citations": [], "step_count": step}

        tool, result = state["selected_tool"], state["tool_result"]

        if tool == "search_documents":
            if result.get("ambiguous_policy_version"):
                amb = result["ambiguous_policy_version"]
                versions = ", ".join(
                    f"{d['document_id']} (version {d['version']})" if d["version"] else d["document_id"]
                    for d in amb["documents"]
                )
                return {
                    "answer": f"{amb['message']} Candidates: {versions}.",
                    "citations": [],
                    "status": "ambiguous_policy_version",
                    "step_count": step,
                }
            chunks = result["chunks"]
            if not chunks:
                return {"answer": "No relevant chunks found.", "citations": [], "status": "no_context", "step_count": step}
            preview = "\n".join(f"- {c['document_name']}: {c['text_preview']}" for c in chunks)
            return {
                "answer": f"Found {len(chunks)} relevant chunk(s):\n\n{preview}",
                "citations": [
                    {"chunk_id": c["chunk_id"], "document_id": c["document_id"], "document_name": c["document_name"]}
                    for c in chunks
                ],
                "step_count": step,
            }

        if tool == "list_documents":
            docs = result["documents"]
            if not docs:
                return {"answer": "No documents available.", "citations": [], "status": "no_context", "step_count": step}
            listing = "\n".join(f"- {d['name']} ({d['chunk_count']} chunks)" for d in docs)
            return {"answer": f"{len(docs)} document(s):\n{listing}", "citations": [], "step_count": step}

        # get_answer_run
        if not result["answer"]:
            return {
                "answer": f"Request {result['request_id']} has no generated answer (status: {result['status']}).",
                "citations": [], "status": "no_context", "step_count": step,
            }
        return {
            "answer": result["answer"],
            "citations": _citations_from_chunk_ids(result["citations"], repo),
            "step_count": step,
        }

    def route_decision(state: AgentState) -> str:
        return "generate_response" if state["status"] == "refused" else "execute_tool"

    graph = StateGraph(AgentState)
    graph.add_node("route", route_node)
    graph.add_node("execute_tool", execute_tool_node)
    graph.add_node("generate_response", generate_response_node)

    graph.add_edge(START, "route")
    graph.add_conditional_edges("route", route_decision)
    graph.add_edge("execute_tool", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()