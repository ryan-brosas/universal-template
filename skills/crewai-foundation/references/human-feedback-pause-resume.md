<!-- capsule-v2 -->
# HumanFeedbackPending pause/resume — exception-as-control-flow with persisted pending context

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How does a flow pause mid-method for human feedback, persist itself, and resume without re-running completed work — and why is the pending signal an Exception subclass?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/flow/async_feedback/types.py:HumanFeedbackPending` (:148); `flow/runtime/__init__.py` `_execute_method` except-arm (:2948), kickoff paused-arm (:2355-2406), `from_pending` (:1199), `resume` (:1285).
**Signature:** `class HumanFeedbackPending(Exception)` carrying `.context: PendingFeedbackContext` (flow_id, method_name, message, emit); `from_pending(flow_id, persistence=None, *, definition=None) -> Flow`.
**Data Shape:** `pending_feedback` table row = UNIQUE(flow_uuid) + context_json + state_json; `save_pending_feedback` writes BOTH a normal state snapshot and the marker in one lock.

### Decisive source
```python
# :2948 inside _execute_method — PAUSED is not FAILED
except Exception as e:
    if isinstance(e, HumanFeedbackPending):
        e.context.method_name = method_name
        if self.persistence is None:
            ...self.persistence = default_flow_persistence()
        # Emit paused event (not failed)
        ...MethodExecutionPausedEvent(...)   # :2962
    elif not self.suppress_flow_events:
        ...MethodExecutionFailedEvent(...)
    raise e

# :2357 at kickoff level — return, don't raise
if isinstance(e, HumanFeedbackPending):
    ...
    self.persistence.save_pending_feedback(
        flow_uuid=e.context.flow_id, context=e.context,
        state_data=state_data)
    ...FlowPausedEvent(...)                  # :2380
    # Wait for events to be processed
    await asyncio.gather(*[asyncio.wrap_future(f) for f in self._event_futures])
    return e        # caller receives the pending exception as a VALUE
```

**Flow:** provider raises `HumanFeedbackPending` → `_execute_method` stamps method name, lazily creates default persistence (SQLite fallback via factory), emits MethodExecutionPausedEvent instead of Failed → kickoff catches it at top level, saves state + pending context, emits FlowPausedEvent, drains event futures, RETURNS the exception → host later builds `MyFlow.from_pending(flow_id)` (loads state+context, ValueError for unknown id) and calls `resume(feedback)` which re-dispatches into `_resume_async_body`, replaying recorded events while suppressing completed methods.
**Invariant:** The signal must be an Exception so it unwinds every intermediate frame without results leaking — but both catch sites must special-case it BEFORE generic failure handling or a pause is mis-recorded as a crash. `resume()` on a flow without pending feedback raises; suppressed-events resumes still emit matched lifecycle pairs (:492 test).
**Probe:** `grep -c 'class HumanFeedbackPending' lib/crewai/src/crewai/flow/async_feedback/types.py` → `1`; `grep -c 'INSERT OR REPLACE INTO pending_feedback' lib/crewai/src/crewai/flow/persistence/sqlite.py` → `1`.
**Direct test:** `tests/test_async_human_feedback.py::test_save_and_load_pending_feedback` (:277), `::test_from_pending_uses_default_persistence` (:431), `::test_from_pending_restores_state` (:456), `::test_resume_without_pending_raises_error` (:567).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "from_pending create a Flow instance from a pending feedback state", limit: 5 });
// → ext-crewAI.lib.crewai.src.crewai.flow.runtime.Flow.from_pending Method flow/runtime/__init__.py 1199+
```

## Verdict
Adopt exception-as-pause-signal with typed Paused-vs-Failed events and the save-on-pause contract. Adapt persistence backend and provider transports. Omit Slack/console providers shipped in `async_feedback/providers.py` (host-specific channels).
