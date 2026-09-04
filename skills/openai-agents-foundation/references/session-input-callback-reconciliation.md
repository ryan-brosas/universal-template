<!-- capsule-v2 -->
# Session-input-callback reconciliation — how can a user callback reorder history without re-persisting old items as new?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** Given an arbitrary callable that may reorder/drop/duplicate `(history, new_input)`, how do you decide which output items belong to the NEW turn and must be appended to the store?

## Identity-then-frequency reconciliation
**Path/Symbol:** `src/agents/run_internal/session_persistence.py:` `prepare_input_with_session` (:317–477), `_build_reference_map` (:1127–1140), `_consume_reference` (:1143–1154), `_build_frequency_map` (:1157–1170), `_session_item_key` (:1101–1124).
**Signature:** `async def prepare_input_with_session(input, session, session_input_callback, session_settings=None, *, include_history_in_prepared_input=True, preserve_dropped_new_items=False, reasoning_item_id_policy=None, wrapper=None) -> tuple[prepared, to_append]`.
**Data Shape:** keys are canonical JSON dumps (`model_dump(exclude_unset=True)` → dict → `json.dumps(sort_keys=True)`; repr fallback); two maps per side: identity refs (key→list of objects) and frequency counts.

### Decisive source
```python
if _consume_reference(new_refs, new_key, item):
    ...
    if id(item) in original_history_object_ids:
        prune_history_indexes.add(combined_index)   # callback moved OLD history around
    else:
        appended.append(item)                        # genuinely new input
    continue
if _consume_reference(history_refs, history_key, item):
    history_counts[history_key] = max(history_counts.get(history_key, 0) - 1, 0)
    prune_history_indexes.add(combined_index)
    continue
...
if new_counts.get(new_key, 0) > 0:
    new_counts[new_key] = max(new_counts.get(new_key, 0) - 1, 0)
    appended.append(item)
```
The callback receives DEEP COPIES, but originals of history are kept alive so `id(item) in original_history_object_ids` still detects recycled history objects. Non-callable callbacks raise `UserError`; non-list returns raise.

**Flow:** load history (honoring `settings.limit`) → normalize + apply reasoning-id policy ON READ (old persisted items may still carry server reasoning IDs) → deep-copy both sides into the callback → classify each returned item: identity-new → append (unless it's actually recycled history) / identity-history or leftover frequency-history → prune / leftover frequency-new → append → sanitize conversation metadata on pruned history positions → drop orphan function calls (with pruning indexes so their outputs go too) → API-normalize → dedupe-prefer-latest.

**Invariant:** Persistence must be derived from PROVENANCE, not position: only items traceable to this turn's input get stored; duplicated content consumes frequency counts exactly once each; prepared model input and persisted items come from the SAME normalization pipeline.

**Probe:** `tests/memory/test_session_limit.py::test_session_limit_drops_unmatched_history_function_call_output` (:69) pins the orphan-drop side; runner-level callback behavior pinned in `tests/test_agent_runner.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "prepare input with session callback reference frequency map", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt identity→frequency classification whenever user code may transform history before it reaches the model; adapt keying to your schema stability; omit the OpenAI-conversation id-stripping variant if your store has stable client-assigned ids.
