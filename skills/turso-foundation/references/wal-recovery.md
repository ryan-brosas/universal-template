<!-- capsule-v2 -->
# WAL recovery — how do you prove which log prefix is trustworthy, and what must a recovery-populated cache re-seed?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How does open-time WAL scanning decide where the valid log ends, and what latent trap exists when it populates caches directly?

## BuildSharedWal: prove, then discard at the first broken link
**Path/Symbol:** `core/storage/sqlite3_ondisk.rs:BuildSharedWal` (:1450-1955), finalize (:1886-1955), regression-comment hole (:1905-1913); authority classification `classify_authority_snapshot_against_wal` (wal.rs :5602-5720).
**Signature:** poll-driven state machine (NeedHeaderRead → AwaitHeader → ChunkLoop → AwaitChunk → Done) over a StreamingWalReader; ~16MB chunks frame-aligned (`BASE / frame_size * frame_size`) so no frame splits across a read boundary.
**Data Shape:** validates header, verifies per-frame salts and cumulative checksum, buffers pending page→frame entries, flushes them into shared cache ONLY when a commit frame arrives.

### Decisive source
```text
// sqlite3_ondisk.rs:1886-1903 / :1917-1955:
// "Only include frames up to last valid commit."
// finalize uses "checksum of last valid commit frame, not necessarily the
//  last frame."
// Stop conditions, logged verbatim: "unexpected page_no, stop reading WAL",
// "salt mismatch, stop reading WAL", "checksum mismatch, stop reading WAL",
// plus liveness guard "No forward progress -- treat as end of valid log."
```

Multi-process (`host_shared`) mode first validates a persisted authority snapshot against the actual WAL, with enumerated rebuild reasons: WalHeaderUnreadable, WalHeaderMismatch, WalLengthMismatch, WalTooShortForSnapshot, LastFrameMissing, LastFrameNotCommit, LastFrameSaltMismatch, LastFrameChecksumMismatch.

The hole closed by a regression comment (:1905-1913): recovery populates the frame cache DIRECTLY rather than via `cache_frame`, so it must seed the rewind-detector high-water mark itself — otherwise the first post-recovery slot reuse goes undetected and find_frame returns a slot now holding a different page, "surfacing as 'non-index page' / 'Invalid page type' / corruption."

**Flow:** validate header → stream chunks → per-frame salt+checksum verify → buffer mappings → publish up to last commit frame → discard torn tail.
**Invariant:** every cache populated outside the normal write path must still satisfy that path's invariants — seed your watermarks.
**Probe:** wal.rs ~8285 truncates ONE byte off the WAL asserting RebuildFromDisk(WalLengthMismatch); zeroed header → WalHeaderUnreadable; end-to-end ~8540 asserts rebuilt max_frame==1, correct last_checksum, loaded_from_disk_scan=true, frame_cache contains 7→[1].

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "BuildSharedWal classify_authority_snapshot rebuild", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "prove-then-discard" prefix semantics and the watermark-seeding rule verbatim; adapt chunk size to your IO; omit authority-snapshot reconciliation unless multi-process. Coverage caveat: none material.
