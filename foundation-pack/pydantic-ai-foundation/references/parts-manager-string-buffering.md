<!-- capsule-v2 -->
# ModelResponsePartsManager string buffering — why are streamed deltas buffered and when do they materialize?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When handling high-frequency stream deltas, how can provider metadata be applied per delta WITHOUT rebuilding (and re-snapshotting) the full accumulated string on every event?

## Buffered string deltas (`_parts_manager.py`)
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_parts_manager.py:ModelResponsePartsManager` — `_string_buffers: dict[int, list[str]]` (:75), `_buffer_string_delta` (:661-677), `_materialized_part` (:679-700), `_materialize_and_cache_part` (:702-708), `_materialized_parts` (:710-718).
**Signature:** `handle_text_delta/handle_thinking_delta/handle_tool_call_delta(...)` yield events while appending content to per-index buffers; reads materialize.
**Data Shape:** `_parts[index]` holds the part with its LAST-MATERIALIZED content; `_string_buffers[index]` holds `[current_value, *pending_deltas]` not yet folded into the part.

### Decisive source
```python
# _parts_manager.py:661-677 — buffer appends only; no part rebuild per delta
def _buffer_string_delta(self, part_index, current_value, delta):
    if not delta: return
    buffer = self._string_buffers.get(part_index)
    if buffer is None:
        buffer = self._string_buffers[part_index] = [current_value or '']
    buffer.append(delta)

# :687-693 — materialization joins once; asserts dict args never mix with string buffering
value = ''.join(buffer)
if isinstance(part, TextPart | ThinkingPart):
    return replace(part, content=value)
...
if isinstance(part, ToolCallPartDelta):
    return replace(part, args_delta=value)

# :133-136 — public reads flush first (only for non-delta slots), then filter deltas out
for part_index in tuple(self._string_buffers):
    if not isinstance(self._parts[part_index], ToolCallPartDelta):
        self._materialize_and_cache_part(part_index)
```

**Flow:** each text/thinking/tool-call delta applies ONLY its metadata (provider name/details) to the stored part and appends raw content to the buffer — the O(len) string rebuild happens once at materialization, not per chunk. Materialization triggers on: `get_parts()`/`get_part_by_vendor_id()` reads, a tool-name arrival forcing a delta→part upgrade (`_apply_tool_call_delta` materializes before applying), replacement of a tracked vendor id, and `__eq__`/`__repr__` via the NON-mutating `_materialized_parts()`. Metadata-only deltas reset their content component so the buffer stays authoritative; when there's no metadata, `provider_details` is defensively copied so an already-emitted event snapshot can't alias manager state. Failure atomicity: `_apply_tool_call_delta` snapshots `buffer_length`, and on ANY exception restores `_parts[i]` + truncates the buffer back (`del buffer[buffer_length:]`) before re-raising — a failed typed promotion leaves prior deltas intact.

**Invariant:** `''.join(buffer)` must equal the result of applying each buffered delta via the `*Delta.apply` chain — both sides combine by plain concatenation; this module DUPLICATES that concatenation and no test catches divergence, so the two must be kept in lockstep. Reading (`__eq__`/`__repr__`) never flushes buffers as a side effect. Dict-typed args bypass string buffering entirely.

**Probe:** `tests/test_parts_manager.py::test_string_deltas_materialize_on_reads_and_replacement` (:89 — interleave metadata-only updates with buffered content across all three part kinds); `::test_tool_call_buffer_changes_are_atomic_when_typed_promotion_fails` (:335 — injected promotion failure discards exactly the failed delta); `::test_incomplete_tool_call_string_arguments_are_buffered` (:225).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "ModelResponsePartsManager _buffer_string_delta _materialize_and_cache_part", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the append-only buffer + read-time materialization pattern for any delta-stream assembler; adopt the snapshot-buffer-length rollback for atomic multi-field updates. Adapt buffer keying if your indices aren't dense ints. Omit the callable-provider-details path unless your adapters need in-place detail resolution. Coverage clean at the pinned commit.
