<!-- capsule-v2 -->
# Synthetic part-end on abort — how do you close a half-streamed message part so the client never sees it stuck "streaming"?

**Source:** pydantic-ai Apache-2.0 `main@fde1bbb6aff461769a1d6d2440c33c232bf90f03` (#7675); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When the stream dies mid-part (error or first-party cancellation), how do you emit a part-end event whose part reflects every delta the client already saw?

## Delta accumulation + synthetic closeout
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py:` `_open_part_deltas` field (:139–142), `_record_part_delta` (:149–161), delta-record wrap around dispatch (:276–283), error-path replay (:298–316).
**Signature:** `def _record_part_delta(self, event: PartDeltaEvent) -> None`; error path: `async for e in self.handle_part_end(PartEndEvent(index=self._open_part_index, part=part)): yield e`.
**Data Shape:** `_open_part_deltas: list[TextPartDelta | ThinkingPartDelta | ToolCallPartDelta]` — parallel journal of deltas applied to `_open_part`, cleared on PartEnd and on new part start.

### Decisive source
```python
def _record_part_delta(self, event: PartDeltaEvent) -> None:
    if event.index != self._open_part_index:
        return                                   # ignore deltas for OTHER parts
    match event.delta, self._open_part:
        case TextPartDelta() as delta, TextPart():
            self._open_part_deltas.append(delta)
        case ThinkingPartDelta() as delta, ThinkingPart():
            self._open_part_deltas.append(delta)
        case ToolCallPartDelta() as delta, ToolCallPart() | NativeToolCallPart():
            self._open_part_deltas.append(delta)
        case _:
            pass

# except-block replay:
for delta in self._open_part_deltas:
    # Synthetic cleanup must not replace the original stream error.
    try:
        match delta, part:
            case TextPartDelta() as text_delta, TextPart():
                part = text_delta.apply(part)
            ...
    except Exception:
        pass                                      # cleanup failure is swallowed
self._open_part = None
self._open_part_deltas.clear()
async for e in self.handle_part_end(PartEndEvent(index=self._open_part_index, part=part)):
    yield e                                       # BEFORE tool-call cleanup / on_error
```

**Flow:** each `PartDeltaEvent` is journaled exactly once around `handle_event` — recorded BEFORE the handler yields it if the handler yields anything, AFTER if it yielded nothing or raised (`delta_recorded` flag :276–283), so recording happens regardless of subclass behavior → on abort: fold all journaled deltas into a COPY of the open part (`delta.apply(part)` rebinds; original untouched) → clear state → yield the synthetic `handle_part_end` FIRST in the except block.
**Invariant:** four rules:
1. The synthetic end's part must equal what a client replaying the received deltas would hold — that's WHY deltas are journaled verbatim and index-matched (`event.index != self._open_part_index` ⇒ ignored; test-pinned).
2. Cleanup must be exception-proof twice over: per-delta `try/except pass` AND a bad `apply` must never replace the original stream error (test pins `ThinkingPartDelta(content_delta='...', provider_details=raising_fn)` degrading to an UNAPPLIED end).
3. Record-before-or-after-dispatch duality: if the handler raises mid-yield after yielding the delta text, recording before dispatch would double-count nothing (recording stores the DELTA object, not handler output) but must happen even when the handler raised before yielding — hence the post-loop `if ... and not delta_recorded` catch.
4. Emit order inside except: synthetic part-end (response side) precedes interrupted-tool-result parts (request side) — clients drop everything after the error chunk.
**Probe:** `.venv/bin/python -m pytest 'tests/test_ui.py::test_cancelled_part_end_contains_accumulated_part' 'tests/test_ui.py::test_cancelled_part_end_ignores_delta_for_different_part' 'tests/test_ui.py::test_part_end_delta_matches_handler_output_on_error' 'tests/test_ui.py::test_part_cleanup_error_does_not_replace_stream_error' -p no:cacheprovider` (anchored at the repo root; 4-case parametrized matrix text/thinking/tool-call/native-tool-call).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_record_part_delta open_part", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the delta-journal + synthetic-end pattern for any streamed-part protocol (SSE frames, websocket chunks, collaborative docs); adapt the apply() mechanics to your part types; omit the four-kind match if your protocol has one part kind — keep the index gate and the swallow-don't-replace rule.
