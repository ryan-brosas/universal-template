<!-- capsule-v2 -->
# Context orchestration — fixed prompt chunk order + tail-preserving summarization

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How does a harness assemble a stable prompt ordering and shrink an over-budget history without losing the most recent turn?

## Fixed assembly order and depth-bounded summarization
**Path/Symbol:** `aider/coders/chat_chunks.py`: `ChatChunks.all_messages()` (:16), `cacheable_messages()` (:57); `aider/history.py`: `ChatSummary.summarize(messages, depth=0)` (:27), `summarize_real(...)` (:33).
**Signature:** `all_messages() -> list[dict]`; `summarize(messages, depth=0) -> list[dict]`.
**Data Shape:** `all_messages` returns one ordered list; `summarize` returns a bounded list, appending a synthetic closing assistant message when the last is not assistant; `summarize_real` returns the original list (fits budget) or `summary + tail`.

### Decisive source
```python
def all_messages(self):
    return (self.system + self.examples + self.readonly_files + self.repo
            + self.done + self.chat_files + self.cur + self.reminder)

def summarize_real(self, messages, depth=0):
    if total <= self.max_tokens and depth == 0:
        return messages
    if len(messages) <= min_split or depth > 3:
        return self.summarize_all(messages)
    # walk backward building the tail up to ~half_max_tokens; ensure the head ends on an assistant message
    tail = messages[split_index:]
    summary = self.summarize_all(sized_head)
    if self.token_count(summary) + tail_tokens < self.max_tokens:
        return summary + tail
    return self.summarize_real(summary + tail, depth + 1)
```

**Flow:** concatenate the eight chunks in fixed order with cache-control on readonly+repo; tokenize; if it fits return as-is; else split at a backward-walked boundary keeping ~half budget as a verbatim tail, ensuring the head ends on an assistant message; summarize the head, and if still over budget recurse up to depth 3, then collapse fully.
**Invariant:** `cur` and `reminder` always last; the most recent assistant turn always survives; recursive depth capped at 3 so pathological histories collapse rather than recurse unboundedly; fixed head stays cache-warm.
**Probe:** `tests/basic/test_history.py::test_too_big`, `test_summarize` assert the tail's final assistant message survives; `test_fallback_to_second_model` covers model absence; fixed order asserted structurally in `chat_chunks.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "all_messages chat_chunks ChatSummary summarize tail", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fixed chunk ordering plus tail-preserving, depth-bounded recursion as the context/compression contract; keep the most recent turn archived-last and the head cache-warm. Adapt the token estimator and cache-control scheme to the host; omit Aider-specific cache headers.
