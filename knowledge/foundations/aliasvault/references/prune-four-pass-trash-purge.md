<!-- capsule-v2 -->
# Four-pass trash prune — how does trash retention purge items AND reclaim their blob bytes?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What are the ordered passes, and why is deletion two-staged (IsDeleted flag then byte-clearing)?

## Pass structure
**Path/Symbol:** `core/rust/src/vault_pruner/mod.rs:134-379` (`prune_vault`), retention default :46-53, entry `get_prune_table_queries` :106-121.
**Signature:** `pub fn prune_vault(input: PruneInput) -> VaultResult<PruneOutput>` with `PruneInput { tables, current_time: String /* ISO-8601 Z */, retention_days: u32 = 30 }`.
**Data Shape:** Input tables come from the pruner's OWN query list; caller-supplied clock string (JS `new Date().toISOString()` documented per-language at :40-44); output = SQL statements + typed stats.

### Decisive source
```rust
// Pass 1 — find items in trash older than retention period.
if let Some(deleted_at_str) = deleted_at.as_str() {
    if let Some(deleted_date) = parse_datetime(deleted_at_str) {
        if deleted_date < cutoff_date { expired_item_ids.push(id.to_string()); }
    }
}
...
sql: "UPDATE Items SET IsDeleted = 1, UpdatedAt = ? WHERE Id = ?".to_string(),
...
sql: "UPDATE Attachments SET IsDeleted = 1, Blob = X'', UpdatedAt = ? WHERE ItemId = ? AND IsDeleted = 0"
```
```rust
// Pass 2 — orphan logo cleanup: a Logo is orphan when no Item with IsDeleted=0 references it.
// Items being purged in Pass 1 are treated as effectively deleted...
// Pass 3/4 — sweep tombstoned attachments/logos that STILL carry blob bytes
// (historical leftovers from older clients inflate the encrypted vault for no reason).
```

**Flow:** Pass 1: items with `DeletedAt < now - retention_days` ⇒ mark item + related FieldValues/TotpCodes/Passkeys `IsDeleted=1` and CLEAR attachment blobs (`Blob = X''`) → Pass 2: logos referenced by NO surviving item ⇒ tombstone + clear FileData in the same call → Pass 3/4: idempotent sweeps clearing bytes from ALREADY-tombstoned rows left by pre-fix clients.
**Invariants:** (1) Soft-delete first, byte-reclaim second — merge LWW still syncs tombstones before bytes vanish. (2) Every UPDATE stamps `UpdatedAt = now` so the prune itself propagates through sync. (3) Related-entity updates carry `AND IsDeleted = 0` so already-deleted children aren't re-counted/re-stamped. (4) The prune NEVER deletes rows — only flags and empties blobs; row removal happens elsewhere. (5) Missing Items table ⇒ success-with-no-op, not an error (:149-158).
**Probe:** `grep -c 'Pass [0-9] —' core/rust/src/vault_pruner/mod.rs` → `5` (passes 1,1,2,3,4 headers); `grep -c "IsDeleted = 1, Blob = X''" core/rust/src/vault_pruner/mod.rs` → `1`; `grep -c "FileData = X''" core/rust/src/vault_pruner/mod.rs` → `3` (2 SQL + 1 test).

## Direct tests
**Path/Symbol:** in-file tests from :447 (fixtures `make_item_record`, logo-orphan case asserting `"FileData = X''"` statement at :806).
**Probe:** run upstream cargo test where toolchain exists; deterministic probes above executed at pin `95903e92`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "prune_vault", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt staged soft-delete→byte-reclaim pruning with self-propagating timestamps; adapt blob column types; omit sql.js execution details. In-file Rust tests exist but were not executed here.
