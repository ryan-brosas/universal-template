<!-- capsule-v2 -->
# UI event-stream transform spine — how does one async generator drive every protocol's stream without letting a hook crash kill bookkeeping?

**Source:** pydantic-ai Apache-2.0 `main@fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you structure a transport-neutral event transformer so protocol subclasses only override `handle_*` hooks while the base class owns ordering, turn tracking, error closeout, and cleanup?

## transform_stream spine + handle_event dispatch
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py:` `UIEventStream.transform_stream` (:208–377), `_turn_to` (:402–421), `handle_event` (:423–501), hook defaults (:618–648); adapter entry `ui/_adapter.py:` `UIAdapter.transform_stream` (:440–455) delegates to a fresh `build_event_stream()`.
**Signature:** `async def transform_stream(self, stream: AsyncIterator[NativeEvent], on_complete: OnCompleteFunc[EventT] | None = None, on_cancel: OnCancelFunc[EventT] | None = None) -> AsyncIterator[EventT]`.
**Data Shape:** `NativeEvent = AgentStreamEvent | AgentRunResultEvent[Any]`; subclass implements exactly one abstract method (`encode_event`) plus optional hook overrides; instance holds per-run bookkeeping (`_result`, `_cancelled`, `_final_result_event`, `_pending_tool_calls`, `_open_part`, `_open_part_index`, `_open_part_deltas`, `_turn`). One transformer instance per HTTP request — it is stateful and not reusable across runs.

### Decisive source
```python
try:
    async for event in stream:
        if isinstance(event, PartStartEvent):
            async for e in self._turn_to('response'): yield e
        elif isinstance(event, PartEndEvent):
            # Only one part is open at a time ... clearing unconditionally is safe either way.
            self._open_part = None
            self._open_part_deltas.clear()
        elif isinstance(event, ToolCallEvent):
            ...
            self._pending_tool_calls[tool_call_id] = _PendingToolCall(kind, event.part.tool_name)
            if kind == 'output':
                # the `FinalResultEvent` backup used by the error path is no longer needed.
                self._final_result_event = None
            async for e in self._turn_to('request'): yield e
        elif isinstance(event, AgentRunResultEvent):
            result = cast(AgentRunResult[OutputDataT], event.result)
            self._result = result
            async for e in self._turn_to(None): yield e
            if on_complete is not None:
                async for e in self._dispatch_callback(on_complete, result): yield e
        elif isinstance(event, FinalResultEvent):
            self._final_result_event = event
        elif isinstance(event, ToolResultEvent):
            self._pending_tool_calls.pop(tool_call_id, None)   # .pop(id, None): tolerate unknown ids
        ... delta recording wraps handle_event ...
        if isinstance(event, PartStartEvent) and isinstance(
            event.part, TextPart | ThinkingPart | ToolCallPart | NativeToolCallPart
        ):
            self._open_part = event.part        # mark open ONLY after start was emitted
            self._open_part_index = event.index
            self._open_part_deltas.clear()
except Exception as exc:
    ... synthetic closeout (see sibling capsules) ...
finally:
    await _utils.aclose_if_supported(stream)
async for e in self._turn_to(None): yield e   # AFTER try: normal path closes the response turn
async for e in self.after_stream(): yield e
```

**Flow:** `before_stream()` → per event: turn transitions fire BEFORE the dispatch → bookkeeping updates interleave with dispatch (`ToolCallEvent` registers pending BEFORE its handler runs; `ToolResultEvent` unregisters; `AgentRunResultEvent` stores result, turns to `None`, then fires `on_complete`) → `handle_event(event)` match-dispatches to 13 overridable handlers → part marked open AFTER its start event yielded → on exception: closeout ladder then `on_cancelled`/`on_error` → `finally` closes the upstream stream → post-try `_turn_to(None)` + `after_stream()` (normal completion only).
**Invariant:** five spine rules:
1. Ordering contract: everything after the ERROR chunk is dropped by clients, so response-side cleanup (close open part) must be yielded BEFORE request-side cleanup (interrupted tool results) inside the except block.
2. A part is "open" for the client only after its start event has been emitted — marking open before emission would make a raising start-hook trigger a synthetic end for a part the client never saw (#7675-era comment).
3. `AgentRunResultEvent` handling stores `_result` BEFORE turning to `None` and before `on_complete` — completion callbacks read fresh state.
4. The `finally` aclose of the upstream stream happens on BOTH paths; `_turn_to(None)`/`after_stream()` happen only on the normal path (in the except branch the cancel/error hooks already ended the protocol conversation).
5. `handle_event`'s match is deliberately non-exhaustive-typed: realtime events get an explicit no-op arm because class patterns cannot reference a union alias (:485–499).
**Probe:** `.venv/bin/python -m pytest tests/test_ui.py -k 'run_stream or cancelled_run_closes_tools or deferred' -p no:cacheprovider` (anchored at `$REFERENCE_ROOT/frameworks/pydantic-ai`; snapshot-pins full event sequences incl. `<stream>/<response>/<request>` wrapper tags).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "UIEventStream transform_stream", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-stateful-transformer spine (bookkeeping-before-dispatch, emit-before-track, cleanup-order-by-client-drop-point, finally-aclose) whenever translating an internal event bus into any wire protocol; adapt the event/hook vocabulary to your protocol; omit the 13-handler fan-out if your protocol needs fewer — the spine works with any subset.
