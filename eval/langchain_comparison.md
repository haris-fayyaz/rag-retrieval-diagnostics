# Custom vs LangChain answer pipeline comparison

Run: `python scripts/compare_answer_pipelines.py`, fake provider/model (no network), 3 documents, 5 questions (4 in-scope + 1 off-topic).

| Case | Custom Chunks | LangChain Chunks | Same Chunks | Same Citations |
|---|---|---|---|---|
| Laptop reimbursement limit | 1_chunk_0, 2_chunk_0, 3_chunk_0 | 1_chunk_0, 2_chunk_0, 3_chunk_0 | Yes | Yes |
| Paid leave days | 2_chunk_0, 1_chunk_0, 3_chunk_0 | 2_chunk_0, 1_chunk_0, 3_chunk_0 | Yes | Yes |
| Leave carryover | 2_chunk_0, 1_chunk_0, 3_chunk_0 | 2_chunk_0, 1_chunk_0, 3_chunk_0 | Yes | Yes |
| Laptop security requirement | 3_chunk_0, 1_chunk_0, 2_chunk_0 | 3_chunk_0, 1_chunk_0, 2_chunk_0 | Yes | Yes |
| Capital of France (off-topic) | 1_chunk_0, 2_chunk_0, 3_chunk_0 | 1_chunk_0, 2_chunk_0, 3_chunk_0 | Yes | Yes |

## Answers

**Did both modes retrieve the same chunks?**
Yes, every case. Expected: retrieval is untouched by pipeline_mode, both call the same retriever on the same repo.

**Did citations remain identical?**
Yes. Both derive citations from `retrieved_chunks`, never from model text, so this is guaranteed by design, not by the model's behavior.

**Did either mode improve answer quality?**
No measurable difference with the fake model (both return the fixed canned text). With real Ollama, answer quality depends only on the prompt string reaching the model, which is the same hardened instructions in both.

**Which implementation was easier to understand?**
Custom. `build_prompt()` is one function, top to bottom. The LangChain version needs `Document`, `ChatPromptTemplate`'s `{var}` semantics, LCEL's dict/`itemgetter` routing, and `Runnable` composition before any of it makes sense.

**What did LangChain simplify?**
Swapping models. `get_chat_model()` returns `FakeListChatModel` or `ChatOllama` interchangeably behind the same `Runnable` interface, and `FakeListChatModel` is built in, no custom fake to write. The LCEL pipeline is also more composable if a step ever needs to change independently (e.g. swap the parser).

**What became harder to trace?**
Exception handling. `ChatOllama` raises `ollama.ResponseError` / raw `httpx` errors that know nothing about this app's `LLMPermanentError`/`LLMTemporaryError` taxonomy. That needed a dedicated translation function (`_translate_exception`) that doesn't exist on the custom path, where `OllamaLLMProvider` raises the right exception type directly. One more layer between a network failure and the code that decides how to react to it.

**Is LangChain useful enough to retain as an optional mode?**
Retain as optional, don't make it default. It doesn't currently do less work than the custom path for this project's scope, and it adds an exception-translation layer that has to be maintained. It's worth keeping because the abstraction pays off once things this project doesn't need yet show up: multiple retrievers behind one interface, structured output parsing, or swapping providers frequently. For a single retriever and a single string answer, it's overhead for its own sake.

## Challenges
- `ChatOllama`'s exception surface isn't documented as clearly as `httpx`'s; had to read `ollama/_client.py` directly to find what it actually raises on connect failure vs HTTP error status.
- `ChatPromptTemplate` treating every `{name}` in every message as a shared input namespace was surprising at first (e.g. `{example_id}` in the system prompt needing to come from the same `invoke()` dict as `context`/`question`).

## What I learned
- LCEL's `|` composition and how `Runnable`s, `itemgetter`, and dict inputs route data between steps.
- `Document`, `ChatPromptTemplate`, `StrOutputParser`, and where LangChain's abstraction boundary sits relative to a hand-rolled pipeline.
- Why exception translation layers exist at framework boundaries, and that they're a real, ongoing maintenance cost, not a one-time task.