<!-- capsule-v2 -->
# Shared-WAL backfill proof — how does a checkpoint prove "these frames are durably in the DB file" to processes that weren't there?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** After a crash, what lets an opener trust (or reject) the claim that nbackfills frames were already backfilled into the main database?

## CRC-sealed proof struct bound to BOTH WAL generation AND DB-file identity
**Path/Symbol:** `core/storage/shared_wal_coordination.rs:470-540` (`SharedWalBackfillProof`, `crc32c()`, `is_structurally_valid()`), install/validate/clear :1391-1505, exclusive-open sanitizer :1513+; header field layout `SharedWalCoordinationHeader` :387-459.
**Signature:** `install_backfill_proof(snapshot: SharedWalCoordinationHeader, db_size_pages: u32, db_header_crc32c: u32)` / `validate_backfill_proof(snapshot, db_size_pages, db_header_crc32c) -> bool`.
**Data Shape:** proof = {nbackfills, max_frame, checkpoint_seq, page_size, salt_1, salt_2, checksum_1, checksum_2, db_size_pages, db_header_crc32c} + version word + crc32c over all of it. "WAL generation identity. A proof must not survive RESTART/TRUNCATE." / "Main-database identity after backfill. This ties the proof to the DB file, not just to the WAL metadata."

### Decisive source
```rust
// :1420-1423 + :1462-1463 — install discipline:
turso_assert!(snapshot.nbackfills != 0, "backfill proof requires positive nbackfills");
...
header.backfill_proof_version.store(SHARED_WAL_BACKFILL_PROOF_VERSION, Ordering::Release);
// :1495-1498 — validation order: structure → CRC → full equality:
if !proof.is_structurally_valid() { return false; }
let stored_crc = header.backfill_proof_crc32c.load(Ordering::Acquire);
if proof.crc32c() != stored_crc { return false; }
proof == SharedWalBackfillProof::from_snapshot_and_db(snapshot, db_size_pages, db_header_crc32c)
```
The multi-release store ordering in `install_backfill_proof` writes version=0 FIRST (invalidating any concurrent validator), then fields, then version last — a poor man's atomic publication over non-atomic fields. Every commit clears the proof (`publish_commit` starts with `clear_backfill_proof`) because new frames invalidate the backfilled prefix claim; zero-progress checkpoints clear it too ("no positive checkpoint claim remains"). Exclusive reopen sanitizes: unsupported version, impossible payloads, or bad CRC ⇒ cleared, never trusted.

**Flow:** checkpoint backfills → sync DB → install proof {snapshot identity + DB identity, sealed} → later crash → opener recomputes both identities and validates equality before honoring nbackfills | mismatch ⇒ classify-and-rebuild path.
**Invariant:** a durability claim is only as strong as its binding to BOTH sides it correlates (log generation × data-file state); validate structure before crypto before equality.
**Probe:** in-file tests: `mapped_shared_wal_coordination_persists_backfill_proof_across_reopen`, `_rejects_corrupt_backfill_proof_crc`, `_rejects_structurally_impossible_backfill_proof`, `_exclusive_reopen_clears_corrupt/_unsupported/_impossible_*` trio, `publish_commit_clears_backfill_proof`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "backfill_proof install_backfill_proof validate_backfill_proof", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sealed-proof correlation for any cross-process durable-progress claim; adapt the identity tuple to your artifacts. Omit the persisted proof entirely if single-process — but keep the clear-on-new-commit rule wherever progress claims exist.
