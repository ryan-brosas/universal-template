<!-- capsule-v2 -->
# HAR recording watchdog — CDP Network events → HAR 1.2 with content modes

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does an agent record HTTPS network activity into a HAR 1.2 file with embed/attach content modes and full/minimal filtering?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/har_recording_watchdog.py` (779 lines): `HarRecordingWatchdog` (:144) — `on_BrowserConnectedEvent` (:158-198), `on_BrowserStopEvent` (:200-207), `_on_request_will_be_sent` (:210-281), `_on_response_received` (:283-365), `_on_data_received` (:367-379), `_on_loading_finished` (:381-425), `_on_loading_failed` (:427-433), `_on_lifecycle_event` (:436-464), `_write_har` (:489+); helpers `_is_https` (:71), `_origin` (:75), `_mime_to_extension` (:88), `_generate_har_filename` (:137).
**Signature:** `_write_har()`; config from `browser_profile.record_har_path` / `record_har_content` (omit/embed/attach) / `record_har_mode` (full/minimal).

### Decisive source
```python
# HTTPS-only: _on_request_will_be_sent returns early unless _is_https(url)
# Content modes:
#   omit  -> no bodies; embed -> base64 text_b64 inline; attach -> write sidecar files
#           (sidecar_dir = <stem>_har_parts/, sha1-hash filename + mime extension)
# Entry assembly per requestId: requestWillBeSent -> responseReceived (status/headers/TLS) ->
#   dataReceived (append latin1 bytes) -> loadingFinished (fetch body via Network.getResponseBody
#   in a task; encodedDataLength -> transfer_size) -> loadingFailed (mark failed)
# Timing: CDP timestamps are monotonic; page onContentLoad/onLoad computed as
#   (lifecycle timestamp - monotonic_start) * 1000, max(0, ...)
# Top-level pages tracked by frameId for page context (startedDateTime from wallTime)
```

**Flow:** on connect (if `record_har_path` set) → enable Network+Page domains → register CDP handlers → on stop → filter entries by mode → assemble HAR 1.2 (entries + pages + log.browser from Browser.getVersion) → write file (sidecars for attach mode).
**Invariant:** only HTTPS is recorded; the response body is fetched at `loadingFinished` (dataReceived may be incomplete) and base64-decoded when `base64Encoded`; timing uses monotonic CDP timestamps (not wall clock) so `onContentLoad`/`onLoad` are correct; the MIME→extension map matches Playwright's behavior.
**Probe:** `tests/ci/browser/test_output_paths.py` (HAR output path handling); no direct HAR-writer unit test in-tree (coverage caveat: live-browser CDP capture).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "HarRecordingWatchdog _write_har _on_loading_finished record_har_content record_har_mode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the HTTPS-only filter, the three content modes, the monotonic-timestamp timing, and the fetch-body-at-loadingFinished pattern. Adapt the CDP Network event API to host.
