<!-- capsule-v2 -->
# Fake-id stream normalization — how do you give placeholder item ids stable identities across deltas, run items, and persistence?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** When a Chat-Completions/LiteLLM backend emits `__fake_id__` for every output item, how are deltas correlated to the right stable id and how do persisted messages avoid colliding?

## StreamIdNormalizer keyed by (agent_run_id, output_index)
**Path/Symbol:** `src/agency_swarm/streaming/id_normalizer.py:StreamIdNormalizer` (whole file, 276L); persistence-side twin `normalize_message_dicts` (:151-184).
**Signature:** `normalize_stream_event(event) -> event` (in-place rewrite + return); `normalize_message_dicts(messages) -> messages`.
**Data Shape:** state maps: `(run_id, output_index) → stable_id`, `(run_id, output_index) → call_id`, pending-id deques per `(run_id, kind)` where kind ∈ {message, reasoning, tool}; generated ids look like `msg_{agent_run_id}_{seq}`.

### Decisive source
```python
# Tool calls: call_id IS the stable id (correlation key for arguments deltas)
if data_type in {"response.output_item.added", "response.output_item.done"}:
    if item.id == FAKE_RESPONSES_ID:
        call_id = getattr(item, "call_id", None)
        stable_id = call_id if valid_call_id else self._get_or_create_stable_id(...)[0]
        self._id_by_run_and_output_index[(agent_run_id, output_index)] = stable_id
...
# Argument deltas rewrite item_id to the RECORDED call_id for that output_index:
if data_type == "response.function_call_arguments.delta":
    call_id = self._call_id_by_run_and_output_index.get((agent_run_id, output_index))
    if call_id is not None: return call_id, False, False

# RunItem events match by KIND against unmatched raw-event indices (deque pairing):
if kind == "tool":  stable_id = call_id or None
if stable_id is None:
    unmatched = self._unmatched_output_indices_by_run_and_kind.get((agent_run_id, kind))
    if unmatched:
        output_index = unmatched.popleft()
        return self._id_by_run_and_output_index.get((agent_run_id, output_index))
stable_id = self._new_seq_id(agent_run_id)     # else allocate + park in pending deque

# Persistence: never leave __fake_id__ in storage — deterministic fallbacks instead
msg_copy["id"] = msg_copy["call_id"] if real_call_id else f"msg_{agent_run_id}_{seq}" (or f"msg_{idx}")
```

**Flow:** raw delta events allocate-or-reuse per output_index; `output_item.added/done` with a real call_id record the index→call_id map; function-call argument deltas then inherit that call_id; RunItemStreamEvents (message/reasoning/tool_created) pair to earlier allocated ids via kind-keyed deques of UNMATCHED indices; anything still fake gets a fresh sequential id parked as pending so later same-kind run items adopt it.
**Invariant:** (1) Determinism within one agent run: same output_index always maps to ONE stable id — consumers keying by item_id never see collisions; (2) call_id beats synthetic ids whenever present because tool-result correlation downstream matches on call_id; (3) dict events pass through untouched (they were already normalized at persistence time); (4) persisted history must never contain the literal placeholder — duplicate ids are legal in the store but `__fake_id__` breaks idempotent replay.
**Probe:** `tests/test_agent_modules/test_stream_id_normalization.py::test_agent_stream_rewrites_fake_ids_in_raw_and_run_item_events` (:19), `test_agent_stream_rewrites_tool_argument_delta_item_id_to_call_id` (:81); cross-plane consistency pinned by `tests/test_agent_modules/test_execution_stream_persistence_fake_id.py` and `tests/integration/litellm_integration/test_litellm_placeholder_ids_integration.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "StreamIdNormalizer FAKE_RESPONSES_ID normalize", limit: 10 });
```

## Verdict
Adopt the (run_id, output_index)-keyed allocation + kind-deque pairing + no-placeholder-in-storage rule; adapt the id format to your own scheme but keep call_id precedence; omit RunItemEvent pairing if your stack only emits raw events. Four direct test files pin this seam at HEAD.
