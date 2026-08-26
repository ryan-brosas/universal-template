<!-- capsule-v2 -->
# HITL pause/resume protocol — how does a flow stop mid-run for human feedback, survive process death, and route the reply when it finally arrives?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What must be persisted at pause time so a webhook handler in ANOTHER process can resume correctly?

## PendingFeedbackContext + HumanFeedbackPending-as-return-value
**Path/Symbol:** `lib/crewai/src/crewai/flow/async_feedback/types.py:19–220` (`PendingFeedbackContext`, `HumanFeedbackPending`); runtime: `_run_human_feedback_step` :3518–3603, `from_pending` :1199–1266, `_resume_async_body` :1389–1600; kickoff catch :2385–2408; sqlite marker `save_pending_feedback` :205–244.
**Signature:** `from_pending(cls, flow_id: str, persistence=None, *, definition=None, **kwargs) -> Flow[Any]`; `resume_async(self, feedback: str = "") -> Any`.
**Data Shape:** context carries `flow_id, flow_class, method_name, method_output, message, emit, default_outcome, metadata, llm(dict|str), requested_at, execution_uuid` — the FULL LLM config serialized because class instances cannot cross processes.

### Decisive source
```python
# kickoff: paused is a RETURN VALUE, not an exception to the caller
if isinstance(e, HumanFeedbackPending):
    if self.persistence is None:
        self.persistence = default_flow_persistence()
    state_data = (self._state if isinstance(self._state, dict)
                  else self._state.model_dump())
    self.persistence.save_pending_feedback(
        flow_uuid=e.context.flow_id,
        context=e.context,
        state_data=state_data,
    )
    ...
    return e
```
```python
# resume: collapsed outcome routes listeners, real output is preserved
self._completed_methods.add(FlowMethodName(context.method_name))
await asyncio.to_thread(
    self._persist_method_completion, FlowMethodName(context.method_name)
)
self._pending_feedback_context = None
if self.persistence is not None:
    self.persistence.clear_pending_feedback(context.flow_id)
```

**Flow:** method decorated with human_feedback runs → provider raises or returns → blocking providers run via `asyncio.to_thread`; async-pause providers raise `HumanFeedbackPending` → framework auto-saves state + context (provider never calls save itself) and emits `FlowPausedEvent` → kickoff RETURNS the exception object (`return e`) instead of raising → later, `MyFlow.from_pending(flow_id)` rebuilds the instance from the stored snapshot, sets `_is_execution_resuming=True` and seeds `_flow_match_id` so usage events match under foreign flow contexts → `resume(feedback)`: sync wrapper REFUSES inside a running loop (`raise RuntimeError ... use 'await flow.resume_async'` :1329–1334) → finalize collapses free text to one of `emit` outcomes (LLM structured-output with literal-typed pydantic model, fallback ladder ending in `emit[0]`) → mark completed, clear pending marker atomically-ish, dispatch listeners on outcome.
**Invariant:** The pause marker row is UNIQUE per flow (`INSERT OR REPLACE`); clearing happens AFTER persisting completion so a crash between them re-offers the same step (at-least-once). Resumed leg emits an UNGATED FlowStartedEvent first — suppressing it broke every started/finished pairing (in-source comment :1392–1400). Outcome routing uses the collapsed label as trigger while `method_outputs` records the ORIGINAL output via the stash dict (:2919–2926).
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_async_human_feedback.py::TestFlowResumeWithFeedback" -q` (expect 12 passed incl. cross-process restore + missing-id raise).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "from_pending resume_async pending feedback pause HumanFeedbackPending", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt serialize-everything-context + return-don't-raise pause + clear-marker-after-completion; adapt LLM config serialization to your provider layer; omit outcome collapsing only if feedback is already categorical. Direct tests executed green at pin.
