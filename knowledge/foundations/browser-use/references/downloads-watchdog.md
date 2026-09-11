<!-- capsule-v2 -->
# Downloads watchdog — auto-download policy, filename sanitization, remote/local completion

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does a browser agent decide what to auto-download, sanitize filenames, and report completion for both local and remote browsers?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/downloads_watchdog.py` (1,503 lines): `DownloadsWatchdog` (:107) — `_should_auto_download_network_response` (:91-104), `_is_generic_text_attachment` (:77-88), `_sanitize_download_filename`, `register_download_callbacks` (:146-168), `download_will_begin_handler` (:311-362), `download_progress_handler` (:364-477), `attach_to_target` (:307+), `_track_download`.
**Signature:** `_should_auto_download_network_response(url, content_type, is_pdf, is_download_attachment, suggested_filename) -> bool`; `_sanitize_download_filename(name) -> str`.

### Decisive source
```python
# Auto-download policy:
#   is_pdf -> True; not is_download_attachment -> False;
#   _is_generic_text_attachment (text/plain|json|js AND no file ext AND generic stem
#     in {'f','download','response','data','callback'} AND ext in {'','txt','json'}) -> False
#   else True
# Filename sanitize (at ingress, so every downstream consumer sees a safe basename):
#   keep only basename (strip ../, absolute, Windows backslash, mixed separators);
#   pure traversal -> 'download'; strip NUL bytes; empty/None -> 'download'
# Completion (remote branch): call complete callbacks FIRST then emit FileDownloadedEvent,
#   else click handlers waiting on on_download_complete time out even though download finished (#5132)
```

**Flow:** `download_will_begin` sanitizes the suggested filename at ingress, caches `_cdp_downloads_info[guid]`, calls start callbacks + emits `DownloadStartedEvent`; `download_progress` calls progress callbacks + emits `DownloadProgressEvent`, and on `completed` tracks the file (local: filePath or filesystem-diff against initial snapshot; remote: fallback to downloadPath+suggestedFilename, call complete callbacks then emit `FileDownloadedEvent`, then delete the guid cache).
**Invariant:** the generic-text-attachment heuristic prevents auto-saving JSON/text API responses as files; filename sanitization happens ONCE at ingress so no downstream consumer can be path-traversed; the remote completion branch MUST invoke complete callbacks (not just the event) or the click-download waiter hangs.
**Probe:** `tests/ci/test_downloads_watchdog.py` (auto-download policy matrix), `tests/ci/security/test_download_filename_sanitization.py` (traversal/NUL/empty cases), `tests/ci/test_remote_download_complete_callback.py` (remote callback + cache-clear).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "DownloadsWatchdog _should_auto_download_network_response _sanitize_download_filename register_download_callbacks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the auto-download policy matrix, the single-point filename sanitization, and the local-vs-remote completion split (callbacks before event). Adapt CDP download events to host.
