<!-- capsule-v2 -->
# Cross-repo pattern: pause-as-return HITL — crewAI's HumanFeedbackPending return vs autogen/agno approval-gated tool calls

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744` (`kickoff_async` :2385–2408 `return e`, `from_pending`/`resume_async` :1199/:1338); cross-ref fleet precedent agno `run/approval.py` approval gates ([DONE:330] capsule set) and agency-swarm guardrail-retry loop. Codebase Memory projects `ext-crewAI`, `ext-agno`. **Question:** When a long-running agent must wait indefinitely for a human, what control-flow shape survives process restarts?

## Pattern: terminal-pause object returned, not raised; resume reconstructs from persisted context
**Path/Symbol:** crewAI `HumanFeedbackPending(Exception)` docstring "Not an error, a control flow signal" (`async_feedback/types.py:148–220`); framework auto-persists then RETURNS the exception instance to the caller.
**Signature:** `kickoff() -> Any | HumanFeedbackPending`; `MyFlow.from_pending(flow_id) -> Flow`; `resume(feedback) -> Any`.
**Data Shape:** persisted `PendingFeedbackContext` = full resume envelope (method, output shown, emit outcomes, default outcome, serialized LLM config, execution uuid).

### Decisive source
```python
class HumanFeedbackPending(Exception):
    # noqa: N818 - Not an error, a control flow signal
    """...
    The caller receives this as a return value from `flow.kickoff()`,
    enabling graceful handling of the paused state without try/except blocks:
        result = flow.kickoff()
        if isinstance(result, HumanFeedbackPending):
            ..."""
```
```python
# engine side — persist-then-return inside the kickoff catch
self.persistence.save_pending_feedback(
    flow_uuid=e.context.flow_id, context=e.context, state_data=state_data,
)
crewai_event_bus.emit(self, FlowPausedEvent(...))
return e
```

**Flow:** provider signals pause by raising the sentinel INSIDE the engine → engine catches at the method/kickoff boundary → persists state + context + marker row (UNIQUE per flow, INSERT OR REPLACE) → emits paused event → returns the object as a normal value → an unrelated process later calls from_pending(id).resume(text), which replays completed methods' effects and routes on the collapsed outcome.
**Invariant:** Three-way contract shared with agno's approval plane and agency-swarm's guardrail loop: (1) pause is DATA crossing an API boundary, never an escaped exception; (2) everything needed to continue lives in PERSISTED context because the resumer may be another process days later; (3) exactly-one pending slot per execution prevents lost or double resumes.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_async_human_feedback.py::TestFlowResumeWithFeedback" -q` (expect 12 passed); static anchor: `grep -c "return e$" lib/crewai/src/crewai/flow/runtime/__init__.py` → 4 (:1557/:1983/:2016/:2406).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "HumanFeedbackPending pause return from_pending resume webhook", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pause-as-data for any human-latency gate; adapt context fields to your domain; omit outcome collapsing if your gate is binary approve/reject with fixed labels.
