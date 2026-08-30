<!-- capsule-v2 -->
# Proxy memory injection — how does an OpenAI-compatible `chat.completions.create` wrapper enrich prompts with memories without blocking or double-counting?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** where do memories get added vs fetched relative to the LLM call, which scope key is mandatory, and what differs between OSS Memory and platform MemoryClient result shapes?

## Connected graph-selected seam
**Path/Symbol:** `mem0/proxy/main.py`: `Mem0.__init__` client fork (:22-33), `Completions.create` gate ladder (:45-140; scope-key ValueError :90-91; function-calling capability probe :93-96), `_prepare_messages` (:142-145), `_async_add_to_memory` daemon thread (:147-159), 6-message search window (:161-172), dual-shape formatting (:174-184). Direct tests `tests/test_proxy.py` (`test_completions_create` :67, system-message variant :89, and the messages-default-aliasing regression :107 "does_not_leak_between_calls").
**Signature:** `create(model, messages=None, *, user_id=None, agent_id=None, run_id=None, metadata=None, filters=None, top_k=10, **all_litellm_kwargs)` — mirrors the full OpenAI Chat Completions surface.
**Data Shape:** response rows: OSS `Memory.search` returns `{"results": [{"memory": ...}], "relations": [...]}` while MemoryClient returns a bare list of `{"memory": ...}` dicts; enriched user content is the fixed template `- Relevant Memories/Facts: …\n\n- Entities: …\n\n- User Question: …`.

### Decisive source
```python
if not any([user_id, agent_id, run_id]):
    raise ValueError("One of user_id, agent_id, run_id must be provided")
if not litellm.supports_function_calling(model):
    raise ValueError(f"Model '{model}' does not support function calling. ...")

prepared_messages = self._prepare_messages(messages)          # prepend MEMORY_ANSWER_PROMPT if no system
if prepared_messages[-1]["role"] == "user":
    self._async_add_to_memory(messages, ...)                  # fire-and-forget BEFORE the LLM call
    relevant = self._fetch_relevant_memories(...)             # SYNCHRONOUS search blocks the call
    prepared_messages[-1]["content"] = self._format_query_with_memories(messages, relevant)
response = litellm.completion(model=model, messages=prepared_messages, ...)
```
```python
def _async_add_to_memory(self, ...):
    threading.Thread(target=add_task, daemon=True).start()    # daemon ⇒ dies with process, never awaited
# only the last 6 messages become the search query
message_input = [f"{m['role']}: {m['content']}" for m in messages][-6:]
```

**Flow:** ctor picks MemoryClient (api_key present) else Memory.from_config → create validates scope + capability → last-user-message branch: memory WRITE starts on a daemon thread immediately (raw original messages), memory READ runs synchronously with top_k default 10 over the last 6 turns → user content REPLACED by the memories/entities/question template → litellm.completion executes → telemetry event captured per client type. Non-user-final conversations skip all memory plumbing entirely.
**Invariant:** (1) exactly ONE of user_id/agent_id/run_id is REQUIRED — an unscoped proxy call is refused before any I/O; (2) add is async-fire-and-forget but search is synchronous — inverting this stalls the write behind the LLM latency budget; (3) the ORIGINAL messages (not enriched) are what get stored as memory; (4) `messages=None` default must not be mutated across calls (the :107 test pins the classic mutable-default leak); (5) result-shape divergence means a porter MUST keep the isinstance fork — reading `["results"]` on a MemoryClient list raises TypeError.
**Probe:** `tests/test_proxy.py::test_completions_create_messages_default_does_not_leak_between_calls`, `::test_completions_create_with_system_message` (no second system prompt injected).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_async_add_to_memory _fetch_relevant_memories _format_query_with_memories", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the write-async/read-sync split, the mandatory scope-key gate, and the original-messages-stored rule verbatim; adapt the enrichment template and window size (-6) to your product's prompt budget; omit litellm if you call providers directly (keep the supports_function_calling-style upfront capability refusal).
