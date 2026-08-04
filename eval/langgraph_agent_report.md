# LangGraph Document Assistant: manual comparison

Run: offline, deterministic RuleBasedRouter (no network, no real Ollama available in this environment), 2 documents, one containing a prompt-injection attempt.

| Case | Selected tool | Expected | Correct? | Steps |
|---|---|---|---|---|
| Direct document question | search_documents | search_documents | Yes | 3 |
| List available documents | list_documents | list_documents | Yes | 3 |
| Inspect an existing audit run | get_answer_run | get_answer_run | Yes | 3 |
| Unsupported request | none (refused) | none | Yes | 2 |
| Document with prompt-injection text | search_documents | search_documents | Yes | 3 |

## Failure and safety observations

- Refused requests stop at 2 steps, execute_tool never runs, confirmed by step count, not just by reading the code
- Prompt-injection text stored inside a document did not change routing or trigger a second tool call, the router never reads document content, only the user's query
- Citations matched retrieved chunk IDs exactly in every case, none invented
- All 5 cases finished within the step limit, no loops

## Did LangGraph add useful value?

- Yes, for the conditional branch specifically. add_conditional_edges cleanly expresses "skip tool execution when refused" in a way a hand-written if/else chain would do just as correctly, but LangGraph makes the branch structure visible and enforces it can't loop back
- For everything else here (a single tool call, no multi-step reasoning), a plain function would have been simpler. The value shows up once more than one conditional path or step exists, not for a single linear pipeline