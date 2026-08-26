<!-- capsule-v2 -->
# Recording-as-folder + marker — how does action recording survive across CLI invocations without touching the daemon?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** A recording must persist between separate process invocations and never break the run — what is the state model?

## folder + marker file + ACTIONS whitelist + never-raise observe
**Path/Symbol:** `src/browser_harness/recorder.py:start_recording` (:97-112), `stop_recording` (:115-125), `observe` (:237-258), `_capture` (:261-291), `recording_dir` (:128-134).
**Signature:** `start_recording(name=None, title=None) -> str`; `stop_recording() -> str|None`; `observe(name, args, kwargs, duration=None)` (never raises).
**Data Shape:** recording = `<workspace>/recordings/<name>/` with `meta.json`, `events.jsonl`, `NNNN.jpg` frames; active state = marker file `.active-<BU_NAME>` holding the dir path.

### Decisive source
```python
ACTIONS = {"goto_url","click_at_xy","type_text","fill_input","press_key","scroll",
           "dispatch_key","upload_file","new_tab","switch_tab","close_tab",
           "ensure_real_tab","wait","wait_for_load","wait_for_element","wait_for_network_idle"}

def observe(name, args, kwargs, duration=None):
    if name not in ACTIONS: return          # read-only helpers get no frames
    try:
        ... d = recording_dir() ...
        if d is None:
            if not _auto_enabled(): return
            d = str(_auto_start())          # silent auto-start, no stdout
        time.sleep(_SETTLE_SECONDS)         # 0.15s paint settle
        _capture(Path(d), name, args, kwargs, duration)
    except Exception: pass                   # recording must NEVER break the run
```
Frames are written with exclusive `xb` open + retry (concurrency-safe); `_marker()` is keyed by `BU_NAME`.

**Flow:** `run.py:_traced` wraps every helper; success calls `observe` → whitelist check → active-dir resolution (auto-rollover if stale) → settle → screenshot + context + details → append events.jsonl. `start/stop_recording` just write meta + marker.
**Invariant:** only screen-CHANGING helpers get frames (read-only inspection would bloat recordings); recording failures are swallowed at every boundary; state lives in the marker file so the daemon is never touched.
**Probe:** `tests/unit/test_run.py` exercises the traced→observe wiring; auto-rollover + marker semantics are covered in `tests/unit/test_recorder*` (present in repo) — verify exact names at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "recorder observe ACTIONS marker recording_dir", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the folder+marker+whitelist model for any side-effecting observation layer; adapt ACTIONS set and settle timing; omit nothing. Recording must be structurally incapable of crashing the caller.
