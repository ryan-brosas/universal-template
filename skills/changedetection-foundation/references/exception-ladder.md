<!-- capsule-v2 -->
# Exception-typed job ladder — how does one bad watch fail without killing the worker loop?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** How are fetch/diff failures classified and persisted so the worker continues to the next job?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/worker.py:async_update_worker` (:146-410); exception types in `content_fetchers/exceptions/`; `ProcessorException` from `processors/exceptions.py`; `FilterNotFoundInResponse` from `processors/text_json_diff/processor.py`.
**Signature:** One `try:` around `perform_site_check → call_browser (await) → run_in_executor(run_changedetection)` followed by ~12 typed `except` arms, each ending `process_changedetection_results = False` after persisting a user-facing error.
**Data Shape:** Each arm writes via `datastore.update_watch(uuid, update_obj={'last_error': ...})` and selectively saves/clears heavy artifacts (`e.screenshot`, `e.xpath_data`, `e.page_text`) — artifacts are set to None IMMEDIATELY after saving to release memory.

### Decisive source
```python
except ProcessorException as e:
    if e.screenshot:
        watch.save_screenshot(screenshot=e.screenshot)
        e.screenshot = None  # Free memory immediately
    ...
    datastore.update_watch(uuid=uuid, update_obj={'last_error': e.message})
    process_changedetection_results = False
...
else:   # only on FULL success
    update_obj['consecutive_filter_failures'] = 0
    update_obj['last_error'] = False
    cleanup_error_artifacts(uuid, datastore)   # deletes last-error-screenshot.png / last-error.txt
```

**Flow:** Failure taxonomy maps each exception class to a specific user-actionable message + artifact handling: Non200ErrorCodeReceived builds per-status text (403/404/407/500 special-cased), FilterNotFoundInResponse increments `consecutive_filter_failures` and fires a notification at threshold (then RESETS counter — threshold is "notify every Nth consecutive failure", not once-ever), BrowserStepsStepException records `browser_steps_last_error_step`, checksumFromPreviousCheckWasTheSame is a SUCCESS-class (clears last_error, resets edited flag). The success `else:` branch is the only place error state is cleared.
**Invariant:** No fetch failure may propagate out of the per-job try — the outermost handler catches Exception and still reaches `finally` (release UUID, quit browser, gc.collect). Error-state transitions are symmetric: every setter arm has its mirror cleanup on success.
**Probe:** `grep -c 'process_changedetection_results = False' changedetectionio/worker.py` → `15`; `grep -c 'cleanup_error_artifacts' changedetectionio/worker.py` → `3` (def :775 + callsites :311/:420); `grep -c 'consecutive_filter_failures' changedetectionio/worker.py` → `7` (:282/:286/:296 filter arm, :347/:351/:357 step arm, :417 success reset).
**Direct test:** `tests/test_errorhandling.py` exercises backend failure paths; filter-failure threshold logic covered by `tests/test_filter_failure_notification.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "Non200ErrorCodeReceived last_error update_watch", limit: 5 });
// CLI: search_graph '{"project":"ext-changedetection.io","query":"async_update_worker exceptions","limit":5,"detail":"ids"}'
```

## Verdict
Adopt typed-exception→user-message ladders with artifact-scoped cleanup for long-lived job workers. Adapt the taxonomy names. Omit screenshot/xpath plumbing where your fetcher produces none.
