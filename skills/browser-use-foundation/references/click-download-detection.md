<!-- capsule-v2 -->
# Click-with-download detection — click coroutine + download wait ladder

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does a click handler learn that the click triggered a file download and wait for it, without blocking on the event bus?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/default_action_watchdog.py` (3,746 lines): `DefaultActionWatchdog._execute_click_with_download_detection` (:44-222), called from `on_ClickElementEvent` (:337-387) and `on_ClickCoordinateEvent` (:389-449).
**Signature:** `async _execute_click_with_download_detection(click_coro, download_start_timeout=0.5, download_complete_timeout=30.0) -> dict | None`.
**Data Shape:** input is a coroutine that performs the click and returns a `click_metadata` dict (or None). Output: the same dict, augmented with `download` (completed), `download_in_progress` (still active past timeout), or `download_timeout` (stalled) keys. `validation_error` dicts short-circuit before any download wait.

### Decisive source
```python
# Direct callbacks registered on the DownloadsWatchdog — NOT the event bus, so the
# click handler learns of a download synchronously from the CDP handler thread.
downloads_watchdog.register_download_callbacks(on_start=..., on_progress=..., on_complete=...)
try:
    click_metadata = await click_coro
    if isinstance(click_metadata, dict) and 'validation_error' in click_metadata:
        return click_metadata                    # validation errors skip download wait
    try:
        await asyncio.wait_for(download_started.wait(), timeout=download_start_timeout)
        try:
            await asyncio.wait_for(download_completed.wait(), timeout=download_complete_timeout)
            click_metadata['download'] = {...}    # completed path
        except TimeoutError:
            # still active? (progress update <5s ago AND state=='inProgress')
            if time_since_update < 5.0 and state == 'inProgress':
                click_metadata['download_in_progress'] = {...}   # suggest wait action
            else:
                click_metadata['download_timeout'] = {...}       # stalled
    except TimeoutError:
        pass                                        # no download started within grace
    return click_metadata
finally:
    downloads_watchdog.unregister_download_callbacks(...)   # ALWAYS unregister
```

**Flow:** register direct callbacks → await click → on validation_error return immediately → wait `download_start_timeout` for `download_started` → if started, wait `download_complete_timeout` for `download_completed` → merge download info into metadata (completed / in-progress / stalled) → finally unregister.
**Invariant:** callbacks are registered before the click and unregistered in `finally` (no leak across clicks); auto-downloads are ignored (`auto_download` guard); validation errors never trigger a download wait; the progress "still active" heuristic uses a 5s recency window + `state=='inProgress'`.
**Probe:** `tests/ci/test_downloads_watchdog.py` + `tests/ci/test_remote_download_complete_callback.py` (the remote branch pins that complete callbacks MUST fire for click handlers to resolve — issue #5132).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_execute_click_with_download_detection register_download_callbacks download_started", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the direct-callback-over-event-bus pattern for click-triggered downloads (avoids the event-bus round-trip hang); adopt the two-phase timeout ladder and the in-progress-vs-stalled heuristic. Adapt the timeout constants to host.
