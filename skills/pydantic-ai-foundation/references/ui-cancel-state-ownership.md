<!-- capsule-v2 -->
# Cancellation state ownership — where does a UI stream expose the resumable RunCancelled, and why must on_cancel fire before the hook?

**Source:** pydantic-ai Apache-2.0 `main@fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** After a first-party cancellation mid-stream, how does the application get the resume payload (full message history) back out of the transformer?

## .cancelled property + persist-in-on_cancel ordering
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py:` `_cancelled` field (:122), `cancelled` property (:168–171), cancel branch (:360–366); adapter pass-through `run_stream(..., on_cancel=...)` (`_adapter.py:575+`); producer side: agent session translation (see sibling capsule `session-cancellation-translation.md`) and `exceptions.py:268` `RunCancelled` ("first-party... external cancellation wins" contract).
**Signature:** `@property def cancelled(self) -> RunCancelled | None`; hook order in except: `self._cancelled = cancelled` → `_dispatch_callback(on_cancel, cancelled)` → `on_cancelled(cancelled)`.
**Data Shape:** `RunCancelled(AgentRunError)` carries `.all_messages()` + new_message_index/usage/metadata/ids — the ENTIRE resume state rides inside the exception object; `transform_stream`'s `on_cancel` param receives it, and the instance re-exposes it post-stream.

### Decisive source
```python
if cancelled is not None:
    self._cancelled = cancelled
    if on_cancel is not None:
        async for e in self._dispatch_callback(on_cancel, cancelled):
            yield e
    async for e in self.on_cancelled(cancelled):
        yield e
else:
    async for e in self.on_error(exc):
        yield e
```
```python
async def test_run_stream_on_cancel():
    ...
    assert '<cancelled>' in events
    assert completions == []                       # never both complete AND cancel
    assert cancellations == [event_stream.cancelled]
    assert cancellations[0].all_messages()         # resume payload present
```

**Flow:** first-party `RunCancelled` surfaces through the event stream → caught by the spine's `except Exception` → classified (sibling capsule ui-pending-tool-closeout covers the isinstance rule) → stored on the instance BEFORE callbacks → `on_cancel` callback may persist `cancelled.all_messages()` and yield protocol events (e.g. an `<cancelled>` frame) → `on_cancelled` hook emits default error-frame events → property exposes the SAME object to code inspecting the stream after consumption.
**Invariant:** four rules:
1. Mutually exclusive endings: a run ends EITHER via `on_complete` OR via the cancel/error ladder — never both (`completions == []` pinned).
2. Store-before-dispatch guarantees the `.cancelled` property is already set while `on_cancel` runs — reentrancy-safe for callbacks that check it.
3. The identity contract (`cancellations == [event_stream.cancelled]`, same OBJECT) lets callers mutate/persist without a copy step.
4. Success and ordinary errors leave `.cancelled` None and never invoke on_cancel (test-pinned), so "was this run cancelled?" has exactly one truthful source.
**Probe:** `.venv/bin/python -m pytest 'tests/test_ui.py::test_run_stream_on_cancel' 'tests/test_ui.py::test_run_stream_on_cancel_not_called_for_success_or_error' -p no:cacheprovider` (anchored at repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "UIEventStream transform_stream", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt store-on-instance-then-callback ordering plus exception-as-resume-payload whenever cancellable work streams progress to clients; adapt the payload fields to your domain; omit the property if your callback always persists synchronously.
