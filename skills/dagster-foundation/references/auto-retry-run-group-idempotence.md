<!-- capsule-v2 -->
# Auto-retry daemon — how are failed runs re-executed exactly once with crash safety?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** How does an event-driven daemon retry failed runs without double-retrying across restarts, and which failures opt out?

## WILL_RETRY tag + run-group idempotence
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/auto_run_reexecution/auto_run_reexecution.py:should_retry` (lines 31-91), `retry_run` (:149-258), `get_automatically_retried_run_if_exists` (:103-115), consumer driver `event_log_consumer.py:run_iteration` (:49-102).
**Signature:** `def should_retry(run: DagsterRun, instance: DagsterInstance) -> bool`; `def retry_run(failed_run: DagsterRun, workspace_context) -> None`.
**Data Shape:** Tags: `WILL_RETRY_TAG`, `AUTO_RETRY_RUN_ID_TAG`, `RETRY_NUMBER_TAG` (= len(run_group)), `RETRY_STRATEGY_TAG` (default strategy `ReexecutionStrategy.FROM_FAILURE`), `BACKFILL_ID_TAG`. Consumer subscribes ONLY to `DagsterEventType.RUN_FAILURE` and `RUN_SUCCESS` events; fetch limit 500/interval 5s via env.

### Decisive source
```python
existing_retried_run = get_automatically_retried_run_if_exists(
    instance=instance, run=failed_run, run_group=run_group_list
)
if existing_retried_run is not None:
    # ensure the failed_run has the AUTO_RETRY_RUN_ID_TAG set
    if failed_run.tags.get(AUTO_RETRY_RUN_ID_TAG) is None:
        instance.add_run_tags(
            failed_run.run_id, {AUTO_RETRY_RUN_ID_TAG: existing_retried_run.run_id}
        )
    if existing_retried_run.status == DagsterRunStatus.NOT_STARTED:
        # A run already exists but was not submitted.
        instance.submit_run(existing_retried_run.run_id, workspace)
    return

# At this point we know we need to launch a new run for the retry
strategy = get_reexecution_strategy(failed_run, instance) or DEFAULT_REEXECUTION_POLICY
tags = {RETRY_NUMBER_TAG: str(len(run_group_list))}
new_run = instance.create_reexecuted_run(...)
instance.add_run_tags(failed_run.run_id, {AUTO_RETRY_RUN_ID_TAG: new_run.run_id})
...
instance.submit_run(new_run.run_id, workspace)
```
With the docstring guarantee on the consumer: "It's safe to call this method on the same run multiple times because once a retry run is created, it won't create another. The only exception is if the new run gets deleted."

**Flow:** event-log consumer keeps per-event-type cursors in `daemon_cursor_storage` (`EVENT_LOG_CONSUMER_CURSOR-<type>`) and persists them only AFTER handlers complete ("persist cursors now that we've processed all the events through the handlers") → a missing cursor initializes at `get_maximum_record_id()` so enabling never replays history → handler filters terminal runs through `should_retry`: missing WILL_RETRY tag on a FAILED run ⇒ recompute + BACKFILL the tag onto the run ("add the tag to the run so that it can be used in other parts of the system"); backfill-terminal or deleted backfill ⇒ no retry; step-failure with `retry_on_asset_or_op_failure=false` ⇒ no retry + explanatory engine event. Handler failure itself writes `WILL_RETRY=false` ("mark that we will not retry it... so that the tags reflect the state of the system").
**Invariant:** Idempotence lives in the run GROUP: presence of `AUTO_RETRY_RUN_ID_TAG` OR any child with `RETRY_NUMBER_TAG` proves a retry exists (user-initiated retries carry no RETRY_NUMBER_TAG); cursor-after-handlers gives at-least-once delivery, made safe by group-checked creation.
**Probe:** `integration_tests/test_suites/daemon-test-suite/auto_run_reexecution_tests/test_event_log_consumer.py::test_get_new_cursor` (:169) + `test_auto_run_reexecution.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "should_retry retry_run consume_new_runs_for_automatic_reexecution", limit: 10 });
```

## Verdict
Adopt tag-backed decision caching + run-group idempotence + cursor-after-handler consumption; adapt ReexecutionStrategy semantics to your engine's resume capability; omit backfill interlock if you have no bulk actions. Direct tests exist for cursor math and end-to-end retry upstream.
