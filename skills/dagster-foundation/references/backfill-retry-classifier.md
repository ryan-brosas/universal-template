<!-- capsule-v2 -->
# Backfill retryable-error classifier — which backfill failures retry and which flip the bulk action to FAILING?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** How does the backfill daemon distinguish transient from permanent errors, and how is the retry budget enforced?

## Exception-class whitelist + failure_count budget
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/backfill.py:_is_retryable_backfill_error` (lines 155-164) + `execute_backfill_iteration_with_instigation_logger` (:167-242) + `_get_max_backfill_retries` (:62-67).
**Signature:** `def _is_retryable_backfill_error(e: Exception) -> bool`; env budget: `DAGSTER_MAX_BACKFILL_RETRIES` (falls back to legacy `DAGSTER_MAX_ASSET_BACKFILL_RETRIES`, default 5).
**Data Shape:** Bulk-action statuses swept each iteration: REQUESTED (in progress), CANCELING, FAILING; terminal statuses skipped via re-fetch before every submission ("refetch, in case the backfill was updated in the meantime"). Jobs sorted by `backfill_timestamp` (oldest first); threaded mode keeps at most one in-flight future per backfill id.

### Decisive source
```python
def _is_retryable_backfill_error(e: Exception):
    # Retry on issues reaching or loading user code, or transient race conditions submitting runs.
    if isinstance(
        e, (DagsterUserCodeUnreachableError, DagsterCodeLocationLoadError, DagsterRunAlreadyExists)
    ):
        return True

    # Framework errors and check errors are assumed to be invariants that are not
    # transient or retryable
    return not isinstance(e, (DagsterError, check.CheckError))

...
if (
    backfill.status == BulkActionStatus.REQUESTED
    and backfill.failure_count < _get_max_backfill_retries()
    and _is_retryable_backfill_error(e)
):
    ...  # user-code class: log "due to unreachable code server and will retry" WITHOUT incrementing
         # other classes: backfill.with_failure_count(backfill.failure_count + 1)
else:
    instance.update_backfill(
        backfill.with_status(BulkActionStatus.FAILING)
        .with_error(error_info)
        .with_failure_count(backfill.failure_count + 1)
    )
```

**Flow:** iteration collects REQUESTED+CANCELING+FAILING backfills → per job: re-fetch, skip if terminal → dispatch asset-backfill (`asyncio.run(execute_asset_backfill_iteration)`) vs job-backfill by `backfill.is_asset_backfill` under a partition-loading context with an optional instigation-scoped logger → on exception classify: whitelisted infra/race classes retry WITHOUT consuming budget (failure_count unchanged — deliberate asymmetry); unknown-but-not-framework errors consume one unit of budget; framework/check invariant errors go straight to FAILING. Budget exhausted ⇒ FAILING with error info persisted on the row.
**Invariant:** The default-deny-but-invariant-exempt classifier means unexpected low-level exceptions (network blips not in the whitelist) still retry up to 5 times, while assertion-style bugs fail fast. User-code unreachability must NEVER burn budget — code-server downtime would otherwise kill every running backfill.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_backfill.py` and test_backfill_failure_recovery.py (retry/FAILING transitions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "_is_retryable_backfill_error execute_backfill_iteration_with_instigation_logger", limit: 10 });
```

## Verdict
Adopt the three-tier classifier (whitelist-retry-free / default-budgeted / invariant-fail-fast) and terminal-refetch before dispatch; adapt the exception taxonomy to your stack; omit the InstigationLogger log-storage branch if unused. Direct recovery tests exist upstream.
