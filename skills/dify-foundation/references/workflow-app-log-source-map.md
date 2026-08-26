<!-- capsule-v2 -->
# workflow-app-log-source-map — Which invocations get an audit log row?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** Where is the line between logged and unlogged workflow runs, and when is the row written?

## InvokeFrom→created_from map with debugger/trigger exclusion, written only on INITIAL start
**Path/Symbol:** `api/core/app/apps/workflow/generate_task_pipeline.py:_save_workflow_app_log` (:748-776); caller `_handle_workflow_started_event` (:320-339) gating on `event.reason == WorkflowStartReason.INITIAL`.
**Signature:** `_save_workflow_app_log(*, session: Session, workflow_run_id: str | None)`.
**Data Shape:** Map SERVICE_API→SERVICE_API, OPENAPI→OPENAPI, EXPLORE→INSTALLED_APP, WEB_APP→WEB_APP; DEBUGGER/TRIGGER/PUBLISHED_PIPELINE/VALIDATION return early (no row).

### Decisive source
```python
def _save_workflow_app_log(self, *, session: Session, workflow_run_id: str | None):
    invoke_from = self._application_generate_entity.invoke_from
    match invoke_from:
        case InvokeFrom.SERVICE_API:   created_from = WorkflowAppLogCreatedFrom.SERVICE_API
        case InvokeFrom.OPENAPI:       created_from = WorkflowAppLogCreatedFrom.OPENAPI
        case InvokeFrom.EXPLORE:       created_from = WorkflowAppLogCreatedFrom.INSTALLED_APP
        case InvokeFrom.WEB_APP:       created_from = WorkflowAppLogCreatedFrom.WEB_APP
        case InvokeFrom.DEBUGGER | InvokeFrom.TRIGGER | InvokeFrom.PUBLISHED_PIPELINE | InvokeFrom.VALIDATION:
            # not save log for debugging
            return
    if not workflow_run_id:
        return
    workflow_app_log = WorkflowAppLog(
        tenant_id=..., app_id=..., workflow_id=self._workflow.id,
        workflow_run_id=workflow_run_id,
        created_from=created_from, created_by_role=self._created_by_role, created_by=self._user_id)
    session.add(workflow_app_log)
```
```python
# caller: only the first start of a run writes the log — resumed segments never duplicate it
if event.reason == WorkflowStartReason.INITIAL:
    with self._database_session() as session:
        self._save_workflow_app_log(session=session, workflow_run_id=self._workflow_execution_id)
```

**Flow:** workflow-started event → INITIAL-reason gate → source map (debug/console surfaces excluded) → row insert in its own short transaction. Resumed runs re-emit GraphRunStarted with reason=RESUME (or similar) so no second row appears.
**Invariant:** The INITIAL gate is what makes log rows idempotent across pause/resume; unmapped sources fail closed via early return rather than defaulting to a wrong bucket; missing run id skips silently.
**Probe:** `grep -c 'WorkflowStartReason.INITIAL' core/app/apps/workflow/generate_task_pipeline.py` → 1; direct coverage via pipeline-core suite (`tests/unit_tests/core/app/apps/workflow/test_generate_task_pipeline_core.py`, executed green).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_save_workflow_app_log created_from InvokeFrom map", limit: 10 });
```

## Verdict
Adopt source-mapped audit rows with an initial-start-only gate. Adapt your surface enumeration. Omit OPENAPI if you have no split service API.
