<!-- capsule-v2 -->
# WAL segment CRC chain — how does a mmap'd WAL detect torn writes and recover a consistent prefix?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** What is the on-disk entry framing, how is each entry's integrity chained to the previous one, and what happens to garbage after a crash?

## Chained-CRC32C mmap segments
**Path/Symbol:** `lib/wal/src/segment.rs`: constants (:19-28), `Segment::append` (:336-375), `Segment::open` recovery loop (:265-290), `Segment::truncate` (:392-418), `Segment::entry` (:319-329); flush offset semantics :300-306.
**Signature:** `fn append<T: Deref<Target=[u8]>>(&mut self, entry: &T) -> Option<usize>`; `fn open<P>(path: P) -> Result<Segment>`; `SEGMENT_MAGIC = b"wal"`, `SEGMENT_VERSION = 0`, `HEADER_LEN = 8` (u64 len), `CRC_LEN = 4`.
**Data Shape:** segment file = fixed-capacity mmap; layout per entry: `[u64 len][payload][zero padding][u32 crc]`; running `self.crc` state seeded from header bytes 4..8.

### Decisive source
```rust
// append:
crc = crc32c::crc32c_append(
    !crc.reverse_bits(),                                   // chain seed: bit-reversed previous CRC
    &self.as_slice()[offset..offset + HEADER_LEN + padded_len], // covers len+payload+padding
);
LittleEndian::write_u32(&mut self.as_mut_slice()[offset + HEADER_LEN + padded_len..], crc);
// open (recovery):
let entry_crc = crc32c::crc32c_append(!crc.reverse_bits(), &segment[offset..offset + HEADER_LEN + padded_len]);
let stored_crc = LittleEndian::read_u32(&segment[offset + HEADER_LEN + padded_len..]);
if entry_crc != stored_crc {
    if stored_crc != 0 {
        log::warn!("CRC mismatch at offset {offset}: {entry_crc} != {stored_crc}");
    }
    break; // stop replay at first mismatch or zeroed tail
}
crc = entry_crc;
index.push((offset + HEADER_LEN, len));
```

**Flow:** append writes len → payload → zero-padding (alignment) → chained CRC over the whole framed entry, updates running CRC and in-memory index `(offset, len)` — readable immediately, durable only after flush → on open: read magic/version/capacity/seed, walk entries while they fit and CRC-match, rebuild index exactly up to the last good entry, set `flush_offset = size()` of the recovered prefix so no pre-existing data is re-flushed → truncate drains index tail, restores running CRC by reading the last survivor's stored CRC (`_read_entry_crc`) or the header seed, ZEROES the deleted byte range so post-crash replay cannot resurrect entries, rewinds `flush_offset` to write there next.
**Invariant:** (1) the CRC seed is `!prev.reverse_bits()` — porting with plain prev silently validates corrupt chains; (2) a torn tail is detected by EITHER crc mismatch OR stored_crc==0 sentinel (zeroed region), both just stop replay without erroring the open; (3) recovered-but-unflushed data must not be flushed again (`flush_offset = size()`); (4) truncation zeroes bytes AND rewinds flush_offset together — one without the other either loses durability or resurrects data.
**Probe:** `grep -c "reverse_bits" lib/wal/src/segment.rs` → prints `3` (append chain :363, recovery check :276, test helper :1019 — two production sites + one test). Direct tests: `lib/wal/src/lib.rs::test_record_id_preserving` (:1235), `test_offset_after_open` (:1271), `check_truncate` parametric (:903), plus `test_segment_recovery` module (`#[cfg(test)] mod test_segment_recovery`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "SEGMENT_MAGIC crc32c_append reverse_bits flush_offset truncate zero", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt framing, bit-reversed chaining, zero-sentinel torn-tail policy, truncate-zeroing. Adapt mmap backend and alignment padding to host page sizes. Omit wal-ctl CLI tooling.
