<!-- capsule-v2 -->
# Memory-hygiene finally block — what must a fetch worker release after EVERY job, in what order?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** What is the mandatory post-job cleanup sequence that keeps a 200-worker fleet from leaking browser/content memory?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/worker.py:async_update_worker` finally block (:667-746); mid-job saves (:530-543); `worker_pool.release_uuid_from_processing` call :727.
**Signature:** `finally:` — captures plugin-hook references BEFORE cleanup, then quit → clear_content → del → gc.collect() → finalize hook → release UUID → pop transient status.
**Data Shape:** Heavy per-job objects: `update_handler` (holds fetcher + screenshot + xpath_data), `contents` (full page bytes/text), watch transient `__check_status`.

### Decisive source
```python
finally:
    if uuid:
        finalize_handler = update_handler  # Capture now, before cleanup deletes it
        finalize_watch = watch
        try:
            if update_handler and hasattr(update_handler, 'fetcher') and update_handler.fetcher:
                await update_handler.fetcher.quit(watch=watch)   # browser teardown safety net
        ...
        if update_handler:
            update_handler.fetcher.clear_content()
            update_handler.content_processor = None
            del update_handler
            update_handler = None
        if 'contents' in locals():
            del contents
        import gc
        gc.collect()
        # plugin finalization hook AFTER all cleanup, using captured refs
        apply_update_finalize(update_handler=finalize_handler, ...)
        # release UUID AFTER all cleanup and hooks complete
        worker_pool.release_uuid_from_processing(uuid, worker_id=worker_id)
```

**Flow:** Order is load-bearing: (1) snapshot references for the plugin finalize hook while they still exist; (2) browser quit as backup even though Playwright/Puppeteer self-clean; (3) null-out content processor + delete handler + delete contents; (4) explicit `gc.collect()` because reference cycles across executor threads delay reclamation; (5) run finalize hook with captured refs; (6) ONLY NOW release the UUID claim so `wait_for_all_checks()` covers hooks; (7) pop `__check_status` and emit completion signal.
**Invariant:** The UUID release must be the LAST cleanup step — releasing earlier lets tests/UI observe "idle" while finalize hooks still write files. Screenshot/xpath blobs are also nulled at SAVE time mid-job (`e.screenshot = None`) so both success and failure paths shed big buffers before the next fetch.
**Probe:** `grep -c 'gc.collect' changedetectionio/worker.py` → `2` (mid-job :654 + finally :700); `grep -c 'release_uuid_from_processing' changedetectionio/worker.py` → `1`; `grep -cF 'Capture now, before cleanup deletes it' changedetectionio/worker.py` → `1`.
**Direct test:** `tests/test_queue_handler.py:test_queue_system` final idle assertion depends on release-in-finally; memory guard fixture `measure_memory_usage` used across the suite keeps regressions visible.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "apply_update_finalize cleanup", limit: 5 });
// CLI: search_graph '{"project":"ext-changedetection.io","query":"finalize","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the ordered finally-ladder for any worker holding native/browser resources. Adapt hook names. Omit nothing — every step exists because skipping it leaked in production fleets.
