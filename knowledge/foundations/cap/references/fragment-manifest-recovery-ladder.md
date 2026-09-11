<!-- capsule-v2 -->
# fragment-manifest-recovery-ladder — After a crash, how do you decide which recorded fragments are safe to include in the recovered video?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What is the manifest→probe fallback ladder, and which checks (is_complete, file_size, decodability) gate a fragment's inclusion?

## Trust the manifest first; verify size + init-segment presence; fall back to raw dir scan only when the manifest yields nothing
**Path/Symbol:** `crates/recording/src/recovery.rs:323-456` (`find_complete_fragments_with_init`), fallbacks `:639-718` (`probe_fragments_in_dir`, `probe_m4s_fragments_with_init`, `probe_single_file`), status gate `:199-204` (`should_check_for_recovery`).
**Signature:** `fn find_complete_fragments_with_init(dir: &Path) -> FragmentsInfo { fragments: Vec<PathBuf>, init_segment: Option<PathBuf> }`.
**Data Shape:** Manifest JSON v2 (`FragmentManifest { version, fragments: Vec<FragmentInfo{path,index,duration,is_complete,file_size}>, total_duration, is_complete }`, `CURRENT_MANIFEST_VERSION = 2`); legacy type `"m4s_segments"` with `segments` array tolerated up to version 5.

### Decisive source
```rust
let result: Vec<PathBuf> = entries.iter()
    .filter(|f| f.get("is_complete").and_then(|c| c.as_bool()).unwrap_or(false))
    .filter_map(|f| {
        let path = dir.join(f.get("path")?.as_str()?);
        if !path.exists() { return None; }
        if let Some(expected_size) = expected_file_size(f)
            && let Ok(metadata) = std::fs::metadata(&path)
            && metadata.len() != expected_size { return None; }   // torn tail write
        if Self::is_video_file(&path) {
            if init_segment.is_some() { Some(path) }
            else { match probe_video_can_decode(&path) { Ok(true) => Some(path), _ => None } }
        } else if probe_media_valid(&path) { Some(path) } else { None }
    }).collect();
```

**Flow:** Gate on meta status first — only `InProgress`/`NeedsRemux` are recoverable; `Complete`/`Failed` are terminal (a Failed status is PRESERVED by startup cleanup, never overwritten). Then per segment dir: try manifest → filter complete+size-matching (+decodable when no shared init segment exists, because without init each fragment must self-describe) → if that yields nothing but an init segment was named, retry as a plain sorted `.m4s` scan (`probe_m4s_fragments_with_init`, min size 100 bytes) → last resort unfiltered extension scan with per-file decode probes. Display falls back from fragmented dir to single `display.mp4`; audio falls back through `.ogg`/`.m4a`/`.mp3` siblings. Segments are ordered by numeric `segment-N` suffix (unparseable → u32::MAX sorts last).
**Invariant:** A size mismatch between manifest and disk means a TORN final write — exclude, don't truncate. Without an init segment, every video fragment must prove decodability independently; WITH one, membership suffices (the init carries the moov). Recovery must never flip a Failed recording back to recoverable.
**Probe:** `crates/recording/tests/recovery.rs` — `test_manifest_size_mismatch_detection`, `test_manifest_version_parsing`, `test_incomplete_fragment_skipping`, `test_fallback_to_directory_scan_when_no_manifest`, `test_orphaned_segment_minimum_size`, `test_failed_recording_is_terminal_for_startup_recovery`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "find_complete_fragments_with_init manifest recovery", limit: 10 });
```

## Verdict
Adopt the three-tier ladder and the size/decodability gates. Adapt probe functions to your media stack; keep the min-size constant as a cheap torn-file filter.
