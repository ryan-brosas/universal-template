<!-- capsule-v2 -->
# SavepointWalPos eager-vs-deferred capture — when is the WAL rewind position pinned, and what exactly does ROLLBACK TO undo in a WAL-mode pager?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** At which instant is a savepoint's WAL position captured, why must materialization also happen at write-upgrade, and which page/WAL/cache states does rollback restore as ONE unit?

## The SavepointWalPos unit + capture gates
**Path/Symbol:** `core/storage/pager.rs:SavepointWalPos` (:1244-1248); capture in `open_savepoint_with_kind` (:2185-2193); deferred fill `Pager::materialize_savepoint_wal_positions` (:3030-3049) called from `begin_write_tx` (:3016-3028); storage on `Savepoint.wal_pos: RwLock<Option<SavepointWalPos>>` (:1276).
**Signature:** `struct SavepointWalPos { max_frame: u64, checksum: (u32, u32), checkpoint_seq: u32 }` (Copy; captured as ONE unit).
**Data Shape:** `Option` — `None` = "transaction has never held the write lock (no frames to rewind), or the pager has no WAL" (:1271-1275).

### Decisive source (the dual capture points and their ordering contract)
```rust
// pager.rs :2185-2193 — EAGER arm: only if already inside the write lock
let wal_pos = self
    .wal
    .as_ref()
    .filter(|wal| wal.holds_write_lock())
    .map(|wal| SavepointWalPos {
        max_frame: wal.get_max_frame(),
        checksum: wal.get_last_checksum(),
        checkpoint_seq: wal.get_checkpoint_seq(),
    });

// pager.rs :3023-3026 — DEFERRED arm at write upgrade
wal.begin_write_tx(allowed_auto_actions)?;
// Must run after the upgrade (and any log restart it performed) so
// the positions belong to the current WAL generation.
self.materialize_savepoint_wal_positions();

// pager.rs :3043-3048 — idempotent fill, retry-safe
for savepoint in self.savepoints.read().iter() {
    let mut wal_pos = savepoint.wal_pos.write();
    if wal_pos.is_none() {
        *wal_pos = Some(pos);
    }
}
```

**Flow:** SAVEPOINT opened outside a write tx stores `wal_pos=None` → first successful `begin_write_tx` (write upgrade) fills EVERY unmaterialized frame with the CURRENT generation's (max_frame, checksum, checkpoint_seq) → writes append frames beyond that mark → ROLLBACK TO rewinds WAL to the stored triple. The comment pins WHY materialization runs after the upgrade: an auto-restart inside `begin_write_tx` can rotate the WAL header, changing generations — capturing before it would store positions from a dead generation.
**Invariant:** All three fields move together (a max_frame without its running checksum/checkpoint_seq cannot be validated on rewind). Idempotence under `if wal_pos.is_none()` makes Busy/BusySnapshot upgrade-retry loops safe — a retry that re-runs begin_write_tx must not re-pin later positions. `checkpoint_seq` membership is what lets the WAL reject a rewind across a checkpoint boundary.
**Probe:** `grep -c 'filter(|wal| wal.holds_write_lock())' core/storage/pager.rs` = 1 (eager gate exists in exactly one place) and `sed -n '3030,3049p' core/storage/pager.rs | grep -c 'if wal_pos.is_none()'` = 1 (idempotent fill) and `sed -n '3023,3027p' core/storage/pager.rs | grep -c 'Must run after the upgrade'` = 1.

## Rollback restores FOUR planes as one atomic shape
**Path/Symbol:** `Pager::rollback_to_snapshot` (:2219-2319) — subjournal pre-image loop (:2239-2273), beyond-boundary discard (:2281-2295), WAL rewind + clean-page eviction (:2297-2313), cursor invalidation (:2315-2316).
**Signature:** `fn rollback_to_snapshot(&self, savepoint: &SavepointSnapshot, journal_end_offset: u64) -> Result<()>`.
**Data Shape:** walks subjournal records `(page_id BE u32, page image)` from the savepoint's start_offset to journal_end_offset with a RoaringBitmap dedupe so only the FIRST (oldest) pre-image of each page wins.

### Decisive source (None means no-op — and dirty-vs-clean asymmetry)
```rust
// pager.rs :2297-2307
// No WAL position: the transaction never upgraded to a write
// transaction, so there are no frames to rewind.
if let (Some(wal), Some(wal_pos)) = (&self.wal, savepoint.wal_pos) {
    wal.rollback(Some(RollbackTo {
        frame: wal_pos.max_frame,
        checksum: wal_pos.checksum,
        checkpoint_seq: wal_pos.checkpoint_seq,
    }));
    self.page_cache
        .write()
        .delete_clean_pages_after_wal_frame(wal_pos.max_frame)
```
```rust
// pager.rs :2266-2271 — restored pages stay DIRTY deliberately
// The restored image is the transaction-visible state at the
// savepoint, not necessarily durable state. Keep it dirty so cache
// eviction cannot drop uncommitted changes that predate the
// rolled-back savepoint/statement.
page.set_dirty();
```

**Flow:** (1) subjournal walk restores each page ≤ db_size from its oldest pre-image, re-inserting into cache KEEPING dirty + registering in dirty_pages; (2) truncate subjournal to start_offset; (3) discard every dirty page > db_size — cleared from dirty set BEFORE cache truncate ("or phantom dirty entries survive into commit", :2283-2284) and dropped from cache; (4) if wal_pos present: WAL rollback to the saved triple + evict CLEAN pages beyond max_frame (their content lives only in now-abandoned WAL frames; dirty ones were already restored in step 1); (5) `invalidate_all_cursors()` = SQLite's saveAllCursors at btree.c:4580. The aristo intent on this function states the pairing rule outright: "Restoring the pre-images and discarding the beyond-boundary pages must happen together; dropping either half leaves a live page pointing at zeroed bytes".
**Invariant:** Restored images stay dirty because they represent UNCOMMITTED state (an outer savepoint may still roll back further); eviction of clean pages past the rewind mark prevents stale reads of abandoned frames. Pages beyond db_size are never subjournaled (`subjournal_page_if_required`), so only the explicit discard removes them. A porter who marks restored pages clean invites eviction of the only copy of pre-savepoint data.
**Probe:** `grep -cF 'delete_clean_pages_after_wal_frame' core/storage/pager.rs` = 1 site feeding from `savepoint.wal_pos`; `sed -n '2266,2271p' ... | grep -c 'Keep it dirty'` = 1; `grep -c 'dirty_pages.remove_range((db_size + 1)..);' ...` = 1; `sqlite/conformance/sqlite-sqltests/savepoint.sqltest` test `savepoint-rollback-overflow-issue-6352` (#6352 regression) exercises restore-under-cache-pressure end-to-end.

## Release-time ledger healing + Commit deferral
**Path/Symbol:** `Pager::release_named_savepoint` (:2046-2096); sibling heal in `rollback_to_named_savepoint` (:2164-2167); snapshot/rebuild pair (:1320-1340).
**Signature:** `pub fn release_named_savepoint(&self, name: &str) -> Result<SavepointResult>`.
**Data Shape:** `SavepointSnapshot { kind, start_offset, db_size, wal_pos: Option<SavepointWalPos>, deferred_fk_violations }` — the value-copy used for rollback; rebuilt frames reset write_offset=start_offset and start with an EMPTY page bitmap (:1330-1340).

### Decisive source
```rust
// pager.rs :2060-2076 — bottom-frame release becomes Commit, deferred until success
let result = if matches!(... Named { starts_transaction: true, .. }) && target_idx == 0 {
    SavepointResult::Commit
} else { SavepointResult::Release };
if matches!(result, SavepointResult::Commit) {
    // Defer mutation until transaction commit succeeds. If commit fails
    // (e.g. deferred FK violation), savepoints must remain intact.
    return Ok(result);
}
...
if let Some(parent) = savepoints.last() {
    parent.set_write_offset(journal_end_offset);   // heal parent's tail
} else { ... subjournal.truncate(0) ... }           // last frame out → journal empty
```

**Flow:** RELEASE resolves newest match by exact name (already lowercased at translate — see `savepoint-name-normalization`) → truncates target-and-above → extends the PARENT's write_offset to absorb the released region (nested journals are contiguous, one file) → when no parent remains, truncates the subjournal to 0. ROLLBACK TO instead snapshots the target, rolls pages back, truncates to target_idx keeping it, then RE-PUSHES a fresh frame via `Savepoint::from_snapshot(target.1)` (:2168) — fresh bitmap, write_offset=start_offset.
**Invariant:** A failed commit must leave the stack intact for retry/recovery (deferred-mutation rule) — the connection-level mirror of this is fuzz test `release_root_deferred_fk_failure_can_recover_with_rollback_to`. Parent write_offset healing keeps "journal_end = top frame's write_offset" true at every stack depth; skipping it corrupts the next rollback's journal_end_offset computation (:2149-2152 reads it off `savepoints.last()`).
**Probe:** `sed -n '2077,2095p' core/storage/pager.rs | grep -c 'parent.set_write_offset(journal_end_offset)'` = 1 and `grep -c 'Defer mutation until transaction commit succeeds' core/storage/pager.rs` = 1; direct tests tests/fuzz/savepoint.rs :437/:476/:531/:576 pin root-release FK checks and recovery-by-rollback-to against rusqlite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "SavepointWalPos materialize_savepoint_wal_positions delete_clean_pages_after_wal_frame", limit: 5 });
// turso.core.storage.pager.Pager.materialize_savepoint_wal_positions Method core/storage/pager.rs 3034-3049
// turso.core.storage.page_cache.PageCache.delete_clean_pages_after_wal_frame Method core/storage/page_cache.rs 751-771
// turso.core.storage.pager.SavepointWalPos Struct core/storage/pager.rs 1244-1248
```
Verified live at pin def9a060 (all resolve line-exact); check_index_coverage stdin-JSON on core/storage/pager.rs = no_recorded_issue + metadata_match, generation_matches=true.

## Verdict
Adopt the two-point capture (eager-if-in-write-lock, else idempotent materialization at write-upgrade AFTER any log restart) and the four-plane atomic rollback (subjournal pre-images kept dirty / beyond-boundary discard before cache truncate / WAL rewind triple / cursor invalidation). Adapt the subjournal+WAL duality to whatever undo-log the host has — the invariant to keep is restored-images-stay-dirty plus journal_end-tracks-top-frame. Omit the TODO-noted divergence where SAVEPOINT eagerly opens a read tx (execute.rs :4809-4816 documents SQLite materializes pager savepoints at write-tx begin instead; behavior guidance only). Direct tests: savepoint.sqltest 41 SAVEPOINT ops (@cross-check-integrity tagged incl. issue-6352 overflow regression); tests/fuzz/savepoint.rs named_savepoint_differential_fuzz 2000-step rusqlite parity incl. temp_schema verify query.
