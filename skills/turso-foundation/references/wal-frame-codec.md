<!-- capsule-v2 -->
# WAL frame codec — what makes a SQLite-byte-compatible frame chain self-verifying?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How do I frame a write-ahead log so corruption is detected exactly where it starts and stale frames can never resurrect?

## Checksum chain seeded per generation
**Path/Symbol:** `core/storage/sqlite3_ondisk.rs` codec (:2190-2235; constants :412-417), writer side `core/storage/wal.rs` (:4801-4830).
**Signature:** Frame = 24B header (six big-endian u32s: page_number, db_size, salt_1, salt_2, checksum_1, checksum_2) + page body. `WAL_HEADER_SIZE = 32`, `WAL_FRAME_HEADER_SIZE = 24`, `WAL_MAGIC_LE = 0x377f0682` (`BE = LE | 1`) — verified at :412-416.
**Data Shape:** cumulative Fibonacci-weighted checksum: each frame covers `x[0..8]` then the page body, seeded with the previous frame's value → one unbroken chain from the 32-byte header.

### Decisive source
```text
// sqlite3_ondisk.rs:2190-2235:
// "s0 += x(i) + s1; s1 += x(i+1) + s0" and
// "The checksum values are always stored in the frame header in a big-endian
//  format regardless of which byte order is used."
// wal.rs:4801-4830 — generation seeding:
// "if next_frame_id == 1 { rolling_checksum = (header.checksum_1,
//   header.checksum_2); } … The first frame of a generation always chains from
//  the WAL header checksum, like SQLite's walFrames at mxFrame == 0."
```

The seeding rule prevents a subtle restart corruption: a checksum captured before a RESTART/TRUNCATE would predate the new header; frame 1 must seed from the synced header instead, because "a savepoint rollback can reinstall a position captured in that window." Three properties fall out: torn/garbage tails are detectable at exactly the first bad frame (recovery self-terminates there); salts bind frames to a specific WAL generation so stale frames are rejected rather than resurrected; `db_size > 0` marks commit frames (:507-509) so recovery never exposes a partial transaction.

**Flow:** header seeds chain → each frame's checksum folds header fields + body with previous value → reader stops at first mismatch.
**Invariant:** never seed frame 1 from anything but the current generation's header checksum.
**Probe:** `read_wal_header` (wal.rs:~10060) parses raw bytes asserting magic, file_format 3007000, page_size 4096, checkpoint_seq==1 after TRUNCATE; codec round-trips at ~6570-6640 assert byte-exact decode and rejection of wrong buffer sizes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "WAL_FRAME_HEADER_SIZE rolling_checksum walFrames", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the byte-compatible framing + per-generation seeding verbatim if you need SQLite file compatibility; adapt constants only for non-4096 page sizes; omit the XOR encryption layer unless at-rest protection is required. Coverage caveat: none material — probes pinned to in-file tests.
