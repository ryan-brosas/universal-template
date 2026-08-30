<!-- capsule-v2 -->
# Auto-recording lifecycle — how does always-on capture roll over between tasks without merging unrelated sessions?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What starts/stops/rolls auto-recordings, and what precedence governs env vs config vs explicit?

## Activity-mtime rollover + explicit/auto duality
**Path/Symbol:** `src/browser_harness/recorder.py:auto_recording_setting/set_auto_recording/_auto_start/_auto_is_stale` (:158-234).
**Signature:** `auto_recording_setting() -> (enabled, source)` with source ∈ {BH_RECORD, config, default}; `_auto_is_stale(d)` compares newest *.jpg mtime against `BH_RECORD_IDLE` (default 180s).
**Data Shape:** Preference persisted atomically (tmp + chmod 600 + os.replace) in `<config>/recording.json`; auto dirs named `session-YYYYmmdd-HHMMSS[-n]` with `"auto": true` in meta.json; the `.active-<BU_NAME>` marker carries whichever dir is live.

### Decisive source
```python
def _auto_is_stale(d):
    try:
        if not _is_auto_recording(d):
            return False  # explicit start_recording() never auto-rolls
        frames = list(Path(d).glob("*.jpg"))
        if not frames:
            return False
        newest = max(f.stat().st_mtime for f in frames)
        return (time.time() - newest) > _auto_idle_gap()
    except Exception:
        return False
```

**Flow:** observe(): BH_RECORD=0 vetoes → active recording but auto disabled meanwhile? unlink marker → stale? unlink marker → none active and auto enabled? silent auto-start (no stdout — agents parse it; same-second collisions get -n suffix) → capture. set_auto_recording(False) unlinks the marker ONLY when the active recording is auto — explicit recordings survive.
**Invariant:** A pause since the last ACTION marks task end: idle is measured from FRAME mtimes, not recording start, so long thinking pauses don't split sessions while genuine gaps roll over; explicit recordings NEVER auto-roll; disabling auto never kills a manually-started recording.
**Probe:** No dedicated recorder test suite — coverage caveat; deterministic anchors verified at source :199-206 (_auto_idle_gap), :209-220 (silent start), :223-234 (explicit-never-rolls guard). Preference-write atomicity mirrors the auth/config write pattern.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "auto recording idle roll", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt activity-mtime rollover + explicit/auto duality for always-on capture. Adapt the gap constant. Omit silent-start if humans read your stdout.
