<!-- capsule-v2 -->
# recovery-start-time-fallback — After remuxing a crashed recording, what start_time do audio tracks get when the original meta was lost?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** Why must recovered mic/system-audio start times fall back to the DISPLAY start time rather than zero or None?

## Missing per-track start times inherit the display start so editor offsets stay at 0
**Path/Symbol:** `crates/recording/src/recovery.rs:1654-1659` (`start_time_or_display_fallback`), application in meta rebuild `:1353-1430`, cursor rescan `:1534-1588` (`load_existing_cursors`/`scan_cursor_images`).
**Signature:** `fn start_time_or_display_fallback(original_time: Option<f64>, display_start_time: Option<f64>) -> Option<f64> { original_time.or(display_start_time) }`.
**Data Shape:** Rebuilt `MultipleSegment` reuses original meta values by segment index when present (`original_segments.get(segment_index)`); mic/system-audio entries are dropped entirely when the ogg file is missing or ≤500 bytes (`MIN_VALID_AUDIO_SIZE`).

### Decisive source
```rust
#[test]
fn start_time_fallback_returns_display_value_when_original_missing() {
    let display = Some(0.4374473);
    assert_eq!(
        start_time_or_display_fallback(None, display),
        Some(0.4374473),
        "mic/system audio start_time must align with display when unknown \
         so the editor's offset calculation (latest - start_time) stays at 0",
    );
}
```

**Flow:** Recovery rebuilds each segment's meta from disk artifacts, preferring values recorded before the crash (fps probe of the remuxed display, original device_ids, notch). Any track whose original start_time was lost inherits `display_start_time`. Cursors come from existing meta when non-empty, else are rescanned from `content/cursors/cursor_<id>.png` filenames with zeroed hotspots and no shape.
**Invariant:** The editor computes track offset as `latest_start − start_time`; a None/0 fallback for a mid-timeline display would shift audio against video by the display's own offset. Dropping tiny (<500B) audio files prevents emitting unplayable stub tracks after a crash during startup.
**Probe:** `crates/recording/src/recovery.rs:1691-1711` — tests `start_time_fallback_prefers_original_value`, `start_time_fallback_returns_display_value_when_original_missing`, `start_time_fallback_returns_none_when_display_missing`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "build_recovered_meta start_time fallback", limit: 10 });
```

## Verdict
Adopt `.or(display)` fallback semantics and the 500-byte audio validity floor. Adapt to your meta schema; keep the editor-offset rationale comment.
