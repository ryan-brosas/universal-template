<!-- capsule-v2 -->
# Journal-mode dispatch — how does one binary open both a WAL database and an MVCC database without lying about file formats?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Where does mode selection live, how is it detected from existing files, and what must refuse to open?

## Two supported modes, header-version round-trip, extension-suffix log detection
**Path/Symbol:** `core/storage/journal_mode.rs:11-56` (`enum JournalMode` with strum snake_case attrs; `supported()` = Wal | Mvcc; `as_version()`), `From<Version>` mapping Legacy→Delete, `logical_log_exists` :59-63 (`.db-log` suffix probe), `open_mv_store` :65-109.
**Signature:** `pub fn open_mv_store(io, db_path, flags, durable_storage, encryption_ctx, allocator, experimental_mvcc_passive_checkpoint) -> Result<Arc<MvStore>>`.
**Data Shape:** MVCC's log lives in a SIBLING file `<db>.db-log` (not the SQLite `-wal`); custom `DurableStorage` implementations may replace the on-disk log entirely.

### Decisive source
```rust
// :34-36 — the honest surface:
pub fn supported(&self) -> bool {
    matches!(self, JournalMode::Wal | JournalMode::Mvcc)
}
// :74-81 — fail-closed composition rule:
if encryption_ctx.is_some() && storage.encryption_ctx().is_none() {
    return Err(LimboError::InvalidArgument(
        "encrypted MVCC requires the custom DurableStorage to be configured with encryption"
```
The guard exists because page encryption and a custom DurableStorage compose independently: an encrypted DB whose log writer is plaintext would leak row images into `.db-log`. `open_mv_store` also shows the injection seam — callers pass `Option<DurableStorage>`, else the default Storage binds `<db>.db-log`. The enum carries `#[strum(to_string = "mvcc", serialize = "experimental_mvcc")]`, so CLI/pragma parsing accepts only the experimental spelling while Display says "mvcc" — deliberate surface honesty for an unfinished mode.

**Flow:** open path probes existing artifacts (`logical_log_exists` ⇒ MVCC history) or takes explicit mode → header `Version` ↔ JournalMode round-trip keeps file-format truth → unsupported modes (Delete/Persist/etc.) parse but refuse to run.
**Invariant:** mode, header version, and sidecar-file presence must agree before any write; encryption context must cover EVERY durable artifact or fail closed at open.
**Probe:** module-level unit coverage is thin here — behavior pins live in integration tests under `$REFERENCE_ROOT/memory/turso/tests/`; treat `supported()` + the encryption guard as the contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "JournalMode open_mv_store logical_log_exists Version", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the parse-everything / support-a-subset enum plus fail-closed cross-artifact validation. Adapt suffix conventions to your product. Omit legacy Delete/Truncate/Persist arms entirely unless you need rollback-journal compat.
