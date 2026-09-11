<!-- capsule-v2 -->
# tmp-rescue-and-respawn-groups — How do you salvage in-progress `.m4s.tmp` fragments and mid-recording encoder respawns during recovery?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** When the recorder dies leaving `segment_N.m4s.tmp` files and `respawn-N/` dirs, which bytes are promoted, refused, or grouped?

## Promote complete-tail tmps, refuse truncated ones with a corrupt marker, remux respawn groups separately then concatenate
**Path/Symbol:** `crates/recording/src/recovery.rs:550-631` (`rescue_pending_tmp_fragments`), `:458-548` (`collect_respawn_groups`), respawn-aware finalize at `:1123-1203` (`finalize_to_progressive_mp4_with_health`).
**Signature:** `fn rescue_pending_tmp_fragments(dir: &Path, health_tx: Option<&HealthSender>)`; `fn collect_respawn_groups(dir: &Path, health_tx) -> Vec<(u32 /*n*/, PathBuf /*init.mp4*/, Vec<PathBuf> /*fragments*/)>`.
**Data Shape:** Tmp fragment = `segment_N.m4s.tmp`, valid only when ≥100 bytes (`MIN_VALID_TMP_SIZE`) with no sibling `<name>.m4s.tmp.corrupt` marker and no already-promoted final name; respawn group = dir `respawn-N/` containing `init.mp4` + `segment_<idx>.m4s` files ≥100B.

### Decisive source
```rust
match tail_is_complete(&path) {
    Ok(true) => {}
    Ok(false) => {
        let reason = "truncated_fragment".to_string();
        warn!("Refusing to rescue truncated fragment {}", path.display());
        // emit PipelineHealthEvent::RecoveryFragmentCorrupt + write corrupt marker
        let _ = std::fs::write(&corrupt_marker, &reason);
        continue;
    }
    Err(error) => { /* marker + health event with the error as reason */ continue; }
}
match std::fs::rename(&path, &final_path) { /* promote */ }
```

**Flow:** For each respawn dir (sorted numerically): rescue tmps first, then index fragments by parsed N, sort, and require init.mp4. Finalization remuxes the main manifest group AND each respawn group into separate progressive mp4s (`{stem}.main.mp4`, `{stem}.respawn-N.mp4`); a group that fails to remux is SKIPPED with a warning (its fragments stay on disk for retry), then all group outputs are concatenated into the final file and temps are cleaned. Single-group case degenerates to a plain rename.
**Invariant:** A truncated tail must NEVER be promoted — that's the exact corruption recovery exists to prevent; instead a persistent `.corrupt` marker prevents re-inspection every sweep, and the failure surfaces as a structured `PipelineHealthEvent::RecoveryFragmentCorrupt`. Respawn groups are isolated so one bad encoder restart can't poison the whole recovered video.
**Probe:** `crates/recording/tests/recovery.rs` — `test_inspect_recording_recovers_orphaned_m4s_fragments_with_init`, `finalize_to_progressive_mp4_includes_respawn_fragments`; deterministic pin: `grep -c 'tail_is_complete' crates/recording/src/recovery.rs` (2 = import + call site).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "respawn rescue_pending_tmp_fragments tail_is_complete", limit: 10 });
```

## Verdict
Adopt the tmp-promotion gate (size floor + tail check + corrupt marker + health event) and per-group remux-then-concat. Adapt `tail_is_complete` to your container format.
