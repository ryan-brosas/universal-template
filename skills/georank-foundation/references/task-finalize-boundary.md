<!-- capsule-v2 -->
# Retry-vs-fail task boundary — when does a Celery task stop retrying and finalize quota?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** How do async tasks distinguish "retryable this time" from "final failure" so users see honest status and quota settles exactly once?

## _is_final_attempt ladder + guarded terminal writes
**Path/Symbol:** `backend/app/tasks/process.py`: `_is_final_attempt` :46–49, `_record_company_retry_error` :100–127, `_mark_company_failed` :51–97, `_retry_dispatch_or_finalize` :346–364; twins in `tasks/crawl.py` + `tasks/diagnose.py` (`_finalize_diagnostic_failure`). Task configs: clean (default retries), graph/vectorize `max_retries=3`, StageClaimBusy retries up to 20.
**Signature:** `_is_final_attempt(task) -> bool`; `_mark_company_failed(company_id, error, *, finalize_quota: bool = False, reservation_id=None)`.
**Data Shape:** Transient error text pattern: `"任务将自动重试：{err[:450]}"` (user-visible retry notice); terminal: `pipeline_status=FAILED` + `pipeline_error=err[:500]`.

### Decisive source
```python
def _is_final_attempt(task) -> bool:
    max_retries = getattr(task, "max_retries", None)
    return max_retries is not None and task.request.retries >= max_retries

# retry path — status stays mid-pipeline so the next delivery can claim:
values = {"pipeline_error": f"任务将自动重试：{str(error)[:450]}"}
if retry_status is not None: values["pipeline_status"] = retry_status

# final path — reservation-scoped UPDATE then settle the money:
query = select(Company).where(Company.id == uuid.UUID(company_id))
if reservation_id is not None:
    query = query.where(Company.ai_reservation_id == expected_reservation_id)
...
if finalize_quota and company.ai_reservation_id:
    await record_async_task_usage(db, ..., status_value="error", ...
        charge_recorded_progress_on_error=True)
```
Dispatch failures get their OWN budget: `_retry_dispatch_or_finalize` retries celery.send_task 20×/60s before marking failed — business failure ≠ broker failure.

**Flow:** exception → release provider-stage claim → log structured event → final attempt? ⇒ guarded FAILED write + `finalize_quota=True` settlement (charges recorded progress) : ⇒ retry-notice write keeping status CLAIMABLE + `self.retry(countdown=60)`. Every terminal/retry write is filtered by ai_reservation_id so a stale worker cannot mutate a resubmitted company.
**Invariant:** Only the FINAL attempt flips pipeline_status to a terminal value; intermediate failures must leave the row claimable. Quota settlement happens EXACTLY once at the terminal transition. All state writes carry the reservation-id guard.
**Probe:** `backend/tests/test_ai_quota_concurrency.py::test_terminal_failure*` family + dispatch-retry tests in the same module.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "_mark_company_failed", limit: 5 });
// verified line-exact: process.py :51–97
```

## Verdict
Adopt the attempt-counting finalize ladder + reservation-scoped writes for any queue pipeline with billing side effects; adapt retry counts/notices; keep business-vs-broker retry separation.
