<!-- capsule-v2 -->
# Export choreography with fail-closed teardown — how do you drive a browser-side MediaRecorder export through CDP and guarantee the host's download behavior is restored even on timeout?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What is the correct start/wait/teardown structure for a CDP-driven headless capture that mutates browser-global state?

## _start_export → size-stable poll → _close_editor in finally
**Path/Symbol:** `src/browser_harness/video_render.py:_start_export/_close_editor` (:334-365, :368-395) + `export()` choreography (:413-523, poll :462-471, finally :473-477); transport = `run_harness` (:106-124).
**Signature:** `_start_export(recording, url, webm) -> dict`; `_close_editor(url, previous=None) -> bool`; both inject Python values via `json.dumps(json.dumps(payload))` into generated harness code.
**Data Shape:** payload {url, downloadPath, filename, marker:__BH_VIDEO_RESULT__=}; result line JSON {target, previous, preflight, clicks, started} / {closed:true, downloadsReset}; webm side-file `<name>.webm.crdownload` signals partial; deadline = expected+30s.

### Decisive source
```python
finally:
    if not _close_editor(url, (browser or {}).get("previous")):
        raise RuntimeError(
            "could not restore Chrome download behavior; restart Chrome"
        )
```

**Flow:** _start_export remembers current tab targetId (previous), opens a NEW tab (never hijacks the operator's), gates videoReady at 50ms×100, reads window.videoPreflight() + clickVisibility() a SECOND time server-side, then Browser.setDownloadBehavior(allow, eventsEnabled=True) BEFORE Page.bringToFront and exportVideo(); the JS promise's rejection is captured into window.__exportError rather than raised. export polls until webm exists AND .crdownload vanished AND size is stable across 0.25s. Teardown resets download behavior FIRST (downloads_reset flag survives even when tab ops throw — each close/switch is individually try/excepted), returns downloadsReset===True as the ONLY success signal.
**Invariant:** teardown is FAIL-CLOSED — if download behavior cannot be restored, export RAISES after capturing ("restart Chrome") because leaving allow-and-forget downloads armed on the user's browser is worse than losing one render; previous-target restore keeps the user on their own tab; the double preflight/clickVisibility check catches composition drift between review-time and export-time; marker-prefixed LAST matching stdout line is the return channel (reversed scan) so stray prints can't forge results.
**Probe:** From repo root: `grep -n 'could not restore Chrome' src/browser_harness/video_render.py` → exactly :476 inside `finally:` at :473; `grep -n 'deadline = time.monotonic() + expected + 30' src/browser_harness/video_render.py` → :462; `grep -n 'downloadsReset\|crdownload' src/browser_harness/video_render.py` → :388/:394/:447/:463/:464/:465 cluster; `grep -n 'BH_RECORD' src/browser_harness/video_render.py` → :107 (nested runs never record). No unit test covers export — coverage caveat (requires real browser+ffmpeg).
**Anchored at the repo root.**

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "export webm download behavior editor close", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt remember→new-surface→arm→poll-size-stable→restore-in-finally-with-verdict for any automation that flips global app settings. Adapt polling budget. Never swallow a failed global-state restore.
