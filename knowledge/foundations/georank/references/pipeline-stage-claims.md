<!-- capsule-v2 -->
# Pipeline stage-claim marker — how do Celery workers agree on who owns the next stage without a lock service?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** With only a row's existing error column available, how do you serialize duplicate stage deliveries across workers and detect a dead claimant?

## Error-column epoch lease
**Path/Symbol:** `backend/app/tasks/process.py` `_claim_company_stage` :129–184 (+ `StageClaimBusy` :17, `_resume_company_pipeline` :280–345); twin `_claim_diagnostic_analysis` in `tasks/diagnose.py` :108.
**Signature:** `_claim_company_stage(company_id: str, *, reservation_id, expected_status, stage: str, task_id: str | None) -> bool` (raises `StageClaimBusy` when another LIVE worker holds the stage).
**Data Shape:** Claim marker written INTO `Company.pipeline_error`: `__georank_task_claim__:{stage}:{task_id}:{epoch_seconds}`; cleared (None) on successful stage completion.

### Decisive source
```python
current_error = str(company.pipeline_error or "")
if current_error.startswith("__georank_task_claim__:"):
    claimed_epoch = int(current_error.rsplit(":", 1)[-1])
    if claimed_epoch > now_epoch - 900:
        raise StageClaimBusy(f"{stage} 阶段正由其他任务处理")   # live claim ⇒ retry in 60s
elif current_error and not current_error.startswith("任务将自动重试："):
    return False                        # real persisted failure ⇒ do NOT resurrect
company.pipeline_error = marker         # take the lease
await db.commit()
```
Caller pattern per task:
```python
if not _run(_claim_company_stage(...)):
    _run(_resume_company_pipeline(company_id, reservation_id, "clean"))
    return                              # someone advanced the pipeline — verify & exit
```

**Flow:** SELECT ... FOR UPDATE the company row → status must equal the EXPECTED post-transition status AND ai_reservation_id must match → empty/failed-retry error ⇒ claim by writing the marker → existing fresh (<900s) marker ⇒ StageClaimBusy → task retries with countdown=60 up to 20 times → stale (>900s) marker ⇒ steal the lease. If the claim fails because the stage already completed, `_resume_company_pipeline` re-dispatches the NEXT stage exactly when the DB shows its transition landed — healing a worker crash between commit and celery send.
**Invariant:** A non-claim, non-retry `pipeline_error` is a REAL user-facing failure and must never be overwritten by a late duplicate delivery. Reservation-id equality on every guarded UPDATE is what kills cross-submission races (a resubmitted company gets a NEW reservation id; old in-flight tasks become no-ops).
**Probe:** `backend/tests/test_ai_quota_concurrency.py::test_completed_diagnostic_ignores_duplicate_task_delivery`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "_claim_company_stage", limit: 5 });
// verified line-exact: process.py :129–184
```

## Verdict
Adopt for queue systems without native dedup keys; adapt the 900s lease and marker prefix to your schema; prefer a dedicated column if you can migrate. Direct tests green under real Postgres.
