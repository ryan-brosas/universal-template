<!-- capsule-v2 -->
# resume-graph-restore-committed-value — Why does a resumed run ignore the CURRENT workflow definition?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How do you rebuild a graph for resume without picking up mid-run edits to the workflow?

## Frozen graph re-read from the persisted run row via set_committed_value
**Path/Symbol:** `api/core/app/apps/base_app_generator.py:BaseAppGenerator._restore_workflow_run_graph` (:74-81); called from `api/core/app/apps/workflow/app_generator.py:_generate_worker` (:651-656) when `graph_runtime_state is not None`.
**Signature:** `_restore_workflow_run_graph(*, session, workflow: Workflow, workflow_run_id: str | None)` (staticmethod).
**Data Shape:** Reads `WorkflowRun.graph` (the JSON graph snapshot persisted at original start); writes it onto the freshly-loaded `Workflow` ORM instance bypassing the session's change tracking.

### Decisive source
```python
@staticmethod
def _restore_workflow_run_graph(*, session: Session, workflow: Workflow, workflow_run_id: str | None) -> None:
    if workflow_run_id is None:
        raise ValueError("Workflow run id is required when resuming")
    workflow_run = session.get(WorkflowRun, workflow_run_id)
    if workflow_run is None or workflow_run.graph is None:
        raise ValueError(f"Workflow run graph not found: {workflow_run_id}")
    set_committed_value(workflow, "graph", workflow_run.graph)
```

**Flow:** resume request → worker loads the CURRENT Workflow row → detects resume (injected GraphRuntimeState) → fetches the historical run row → overwrites `workflow.graph` with the frozen snapshot using `set_committed_value` (marks it as already-persistent state, so no UPDATE is ever emitted and no dirty flush races the run) → engine builds the graph from that dict.
**Invariant:** A resumed execution replays EXACTLY the topology it started with — node/edge edits made while paused must not apply mid-flight; `set_committed_value` (not attribute assignment) keeps SQLAlchemy from queueing a write of run-graph data back onto the master Workflow row; missing snapshot is a hard error, not a fallback to current graph.
**Probe:** `grep -c 'set_committed_value' core/app/apps/base_app_generator.py` → 2; `grep -c '_restore_workflow_run_graph' core/app/apps/workflow/app_generator.py` → 1 call site (+def).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_restore_workflow_run_graph set_committed_value resume graph", limit: 10 });
```

## Verdict
Adopt "resume reads its own snapshot" + the committed-value trick. Adapt storage of the snapshot (run table here). Omit nothing — this is the whole anti-drift contract.
