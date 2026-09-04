<!-- capsule-v2 -->
# tool-call delta upgrade ladder + vendor-id tracking — when does a streamed fragment become a real part?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What exact event must a streaming consumer receive as a not-yet-named argument stream matures into a complete tool call — and how do vendor ids route updates to the right slot?

## handle_tool_call_delta / vendor-id map (`_parts_manager.py`)
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_parts_manager.py:handle_tool_call_delta` (:358-466), `handle_tool_call_part` (:468-519), `_vendor_id_to_part_index` (:73), `_typed_call_part` (:114-125), embedded-thinking tag handling (:734-772).
**Signature:** `handle_tool_call_delta(*, vendor_part_id, tool_name=None, args=None, tool_call_id=None, provider_name=None, provider_details=None) -> ModelResponseStreamEvent | None`.
**Data Shape:** Managed items are `ToolCallPartDelta` until they carry a tool name, then upgrade to (possibly typed) `ToolCallPart`/`NativeToolCallPart`; the vendor map translates provider ids → list indices.

### Decisive source
```python
# _parts_manager.py:417-432 — a fragment stays eventless until it's a full part
delta = ToolCallPartDelta(tool_name_delta=tool_name, args_delta=args, tool_call_id=tool_call_id, ...)
part = delta.as_part() or delta
if isinstance(part, ToolCallPart):
    part = self._typed_call_part(part)          # promote via ToolDefinition.tool_kind
new_part_index = self._append_part(part, vendor_part_id)
if isinstance(part, ToolCallPart | NativeToolCallPart):   # ONLY then emit PartStartEvent
    return PartStartEvent(index=new_part_index, part=part)
# else: return None — no event for a still-incomplete part

# :458-466 — an in-place upgrade re-emits PartStart at the SAME index; a plain update
# emits PartDelta, backfilling tool_call_id from the stored part when the delta lacks it
if isinstance(existing_part, ToolCallPartDelta):
    return PartStartEvent(index=part_index, part=updated_part)
else:
    if updated_part.tool_call_id and not delta.tool_call_id:
        delta = replace(delta, tool_call_id=updated_part.tool_call_id)
    return PartDeltaEvent(index=part_index, delta=delta)

# :401-406 — with vendor_part_id None AND tool_name None, attach to the latest matching
# tail; a named call ALWAYS starts fresh (vendors that send names mid-stream rely on this)
```

**Flow:** lookup by vendor id (None ⇒ latest-part-of-type fallback; mismatched type after materialization raises `UnexpectedModelBehavior`) → new fragments append as eventless deltas; once `as_part()` yields a full part, promote its kind from `_tool_kind_by_name` (built at construction from `ToolDefinition.tool_kind`; unknown/hallucinated names stay base class) → emit `PartStartEvent` on creation OR delta→part upgrade (same index), `PartDeltaEvent` on ordinary updates, `None` while incomplete. `handle_tool_call_part` is the non-delta twin: fully overwrite-or-create, generating a tool_call_id when absent. Embedded `<think>` tags split one text slot into Thinking/Text parts by untracking the vendor id at each boundary. `apply_event` replays recorded events through the same paths preserving indexes.

**Invariant:** A consumer sees exactly one `PartStartEvent` per final part (creation or same-index upgrade) — never two starts, never a start without a full part. Vendor-id remapping after overwrite keeps late deltas landing on the replaced slot; `_stop_tracking_vendor_id` prevents stale routing after thinking-tag splits.

**Probe:** `tests/test_parts_manager.py::test_handle_tool_call_deltas` (:597), `::test_tool_call_promotes_after_buffered_arguments_are_materialized` (:306), `::test_cannot_convert_from_text_to_tool_call` (:904), `::test_handle_text_deltas_with_think_tags` (:516).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "handle_tool_call_delta _vendor_id_to_part_index _typed_call_part", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the delta→part upgrade contract (eventless until complete; single PartStart per part; same-index re-start on upgrade); adopt construction-time tool-kind promotion. Adapt the vendor-id keying to your transport's id semantics. Omit embedded think-tag splitting if your providers deliver thinking as native parts. Coverage clean at the pinned commit.
