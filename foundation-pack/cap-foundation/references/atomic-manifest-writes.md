<!-- capsule-v2 -->
# atomic-manifest-writes — How do you write crash-critical JSON (fragment manifests, recording meta) so a crash never leaves torn state?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What is the write ordering (temp file → fsync → rename → dir fsync) and what does the in-progress meta lifecycle look like?

## temp+fsync+rename+dir-fsync; InProgress meta written at START, final meta overwrites at STOP
**Path/Symbol:** `crates/recording/src/fragmentation/mod.rs:11-35` (`atomic_write_json`, `sync_file`); meta lifecycle `studio_recording.rs:1800-1822` (`write_in_progress_meta`) and `:1778-1798` (`persist_final_recording_meta`).
**Signature:** `pub fn atomic_write_json<T: Serialize>(path: &Path, data: &T) -> std::io::Result<()>`.
**Data Shape:** Temp sibling `<name>.json.tmp`; manifest `{version:2, fragments[], total_duration, is_complete}`; `RecordingMeta.inner` carries `StudioRecordingMeta::MultipleSegments{status: InProgress|NeedsRemux|Complete|Failed}`.

### Decisive source
```rust
let mut file = std::fs::File::create(&temp_path)?;
file.write_all(json.as_bytes())?;
file.sync_all()?;
std::fs::rename(&temp_path, path)?;
if let Some(parent) = path.parent()
    && let Ok(dir) = std::fs::File::open(parent)
{
    let _ = dir.sync_all();   // rename durability needs the DIRECTORY fsync
}
```

**Flow:** Recording start (fragmented mode only) writes an EMPTY-segments meta with `status: InProgress` BEFORE the first frame — this is the recovery beacon. Every manifest rotation rewrites via atomic_write_json. Stop writes the final meta with real segments + status (`Complete` or `NeedsRemux` when fragmented display dirs remain). Final-meta save failure only warns ("downstream consumers may see in-progress state") because recovery treats InProgress as merely CANDIDATE — fragments still gate actual recoverability.
**Invariant:** The dir fsync after rename is mandatory on POSIX — without it the rename itself can be lost on power failure, resurrecting stale manifest content. Status is advisory; fragment-level evidence decides recovery. Failed status must be preserved once set (never silently rewritten by later sweeps).
**Probe:** `crates/recording/tests/recovery.rs` — `test_recording_meta_status_serialization`, `test_find_incomplete_requires_meta_file`; deterministic pin: `grep -n 'dir.sync_all' crates/recording/src/fragmentation/mod.rs` (1 hit).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "atomic_write_json FragmentManager write_manifest", limit: 10 });
```

## Verdict
Adopt the four-step durable-write recipe and the start-InProgress/stop-final meta handshake. Adapt serialization; keep failure-to-persist-final non-fatal.
