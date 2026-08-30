<!-- capsule-v2 -->
# Logical log frame format — what does a committed-MVCC-operations journal look like on disk?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How do I frame a replayable commit journal that is independent of the SQLite WAL?

## `.db-log`: 56B header + TX frames, salt-seeded chained CRC32C
**Path/Symbol:** `core/mvcc/persistent_storage/logical_log.rs` module doc (:1-231), constants (:294-354), `LogicalLog` struct (:579+), op encoding (:109-121).
**Signature:** Log header (56B): magic `0x4C4D4C32 "LML2"` | version u8 (v2=2, v3=3) | flags u8 | hdr_len u16 ≥56 | salt u64 (random, regenerated each truncation) | reserved[36] zeroed | hdr_crc32c. TX frame = 24B header (`FRAME_MAGIC "MVTX"`, payload_size u64, op_count u32, commit_ts u64; v3 extension frames use `EXT_FRAME_MAGIC "MVEX"` + 40B header) + variable payload + 8B trailer (crc32c + `END_MAGIC "MVTE"`).
**Data Shape:** ops are `tag u8 | flags u8 | table_id i32 (must be NEGATIVE — canonical MVCC ids) | payload_len varint | payload`; tags: UPSERT_TABLE/DELETE_TABLE/UPSERT_INDEX/DELETE_INDEX/UPDATE_HEADER; flag `OP_FLAG_BTREE_RESIDENT` marks rows that pre-existed MVCC tracking (recovery preserves it because checkpoint/GC logic depends on it); flag `OP_FLAG_PORTABLE_EXTENSION` introduces protobuf-style bytes the parser must consume but may ignore.

### Decisive source
```rust
// logical_log.rs:572-576 — the chain seed:
// "Derives the initial CRC seed from the header salt.
//  The salt is mixed into a 32-bit CRC state that seeds the first frame's
//  checksum."
fn derive_initial_crc(salt: u64) -> u32 { crc32c::crc32c(&salt.to_le_bytes()) }
// trailer: crc32c_append(prev_frame_crc, tx_header || payload); first frame
// seeds from crc32c(salt.to_le_bytes()).
```

The trailer CRC covers TX header + body as written on disk (ciphertext when encrypted). Validation is availability-focused, mirroring SQLite WAL prefix semantics: torn/incomplete tail at EOF accepted as EOF; first invalid frame in forward scan invalidates only the tail; ONLY header corruption fails closed.

**Flow:** commit serializes ops into a LogRecord → frame with header/payload/trailer → append at writer offset → recovery replays forward until first torn frame.
**Invariant:** the running CRC chain is seeded per-generation from the salt — frames cannot be transplanted between logs (different salts ⇒ different chains).
**Probe:** `test_logical_log_rowid_negative_varint_roundtrip` (logical_log.rs:4811) pins round-trip plus deferred-offset readability; `shared_wal_coordination`-style header tests exist in-file; 59 `#[test]`s cover the codec.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "LogicalLog FRAME_MAGIC LOG_HDR_SIZE derive_initial_crc", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the format skeleton (salt-seeded chained CRC + negative table-id canonicalization + btree-resident bit) for any MVCC journal; adapt magics/versioning to your product; omit encryption chunking unless at-rest protection is required. Coverage caveat: probes pinned to in-file unit tests; no integration-runner probe recorded this pass.
