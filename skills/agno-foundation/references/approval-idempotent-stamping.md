<!-- capsule-v2 -->
# Approval idempotent stamping — How are approval records created exactly once across double-fired pause hooks?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What stops two pause events from creating two approval rows for one run?

## Stamp approval_id on tools; second fire short-circuits on the stamped id
**Path/Symbol:** `libs/agno/agno/run/approval.py:create_approval_from_pause` (:152-206) + async twin (:209-271) + `check_and_apply_approval_resolution` (:640-669).
**Signature:** `create_approval_from_pause(db, run_response, agent_id=None, ..., user_id=None, schedule_id=None, schedule_run_id=None) -> Optional[str]`; `check_and_apply_approval_resolution(db, run_id, run_response) -> None`.
**Data Shape:** returns stamped approval_id or None; DB row is a dict built by `_build_approval_dict` (source fields agent/team/workflow with team/workflow overriding agent).

### Decisive source
```python
# Skip if an approval_id is already stamped (avoids duplicates when pause hook fires twice)
for t in tools or []:
    if getattr(t, "approval_type", None) == "required" and getattr(t, "approval_id", None) is not None:
        return getattr(t, "approval_id", None)
try:
    approval_data = _build_approval_dict(...)
    db.create_approval(approval_data)
    approval_id: str = approval_data["id"]
    _stamp_approval_id_on_tools(tools, requirements, approval_id)
except NotImplementedError:
    pass   # db backend without approvals support: silent no-op
except Exception as e:
    log_warning(f"Error creating approval record (sync): {str(e)}")   # degrade, never crash the pause
```

Continue-gate (`check_and_apply_approval_resolution`):
```python
if any(record is None for _, record in pairs):
    raise RuntimeError("No approval record found for this run. Cannot continue a run that requires external approval.")
if any((record or {}).get("status", "pending") == "pending" for _, record in pairs):
    raise RuntimeError("Approval is still pending. Resolve the approval before continuing this run.")
```

**Flow:** pause → create_approval_from_pause stamps id onto ALL approval_type="required" tools (and requirement tool_executions via `_stamp_approval_id_on_tools`) BEFORE cleanup_and_store so the persisted row carries the handle → resolver reads the row, applies status to ToolExecution fields (`_apply_approval_to_tools`) and mirrors them into RunRequirement objects (`_sync_requirements_after_approval`: confirmation bool, per-field values, external result; rejected ⇒ answered=True + requires_confirmation=True/confirmed=False so the reject lane handles it) → resolved approval attached at `run_response.metadata["approval"]` for post-hooks.
**Invariant:** Idempotence lives on the TOOLS, not the DB (no unique-constraint dependency). Creation failures degrade to warning — a broken approvals backend must not crash the pause path. The continue gate FAILS LOUD on missing/pending rows rather than silently executing unapproved work.
**Probe:** `grep -cF 'pause hook fires twice' libs/agno/agno/run/approval.py` → **2** (sync + async twins); `grep -cF 'Approval is still pending. Resolve the approval before continuing this run.' libs/agno/agno/run/approval.py` → **2**; direct behavior tests `libs/agno/tests/unit/run/test_approval.py::TestCreateApprovalFromPause` (:222), `libs/agno/tests/unit/os/test_require_requirement_resolved.py` (see also `test_require_approval_resolved.py`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "create_approval_from_pause check_and_apply_approval_resolution pending", limit: 10, fields: ["signature", "name", "file"] });
```
(resolves acreate_approval_from_pause line-exact 209-271.)

## Verdict
Adopt tool-stamped idempotence + loud pending gates as the approval contract; adapt the record schema/routing fields; omit audit-type records if you only need blocking approvals.
