<!-- capsule-v2 -->
# Loglog serializer chunk streams — how do you serialize a record with ONE reserve and bulk copies instead of byte-at-a-time growth?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What's the write-side contract that lets inline values and borrowed payloads share one length-checked reservation?

## Statically composed chunk chain: encoded_len reserve → copy_to fill → set_len

**Path/Symbol:** `core/mvcc/persistent_storage/logical_log/serializer.rs` — `LogChunkStream` trait :9-18 (`encoded_len() -> Option<usize>` + `copy_to(writer)` + `chain`), `InlineLogChunk<N>` :40-71 (stack array + real prefix len), `BorrowedLogChunk<'a>` :73-85, `LogChunkWriter { output: *mut u8, capacity, written }` :91-117, `try_extend_chunks` macro :124-165, `log_write!` macro :178-206, op-entry wire layout `serialize_op_entry` :288-374 (`tag(1) | flags(1) | table_id(4) | payload_len(varint) | payload`).
**Signature:** `fn try_extend_chunks(&mut self, chunks: impl LogChunkStream) -> Result<()>`; `LogBufferWrite::into_chunks(self) -> impl LogChunkStream`.
**Data Shape:** two varint dialects coexist: `SqliteVarint` (SQLite 9-byte big-endian-ish record format) for on-log payloads, `ProtoVarint`/`ProtoKey`/`ProtoSint64` (protobuf field-key `(field<<3)|wire`, zigzag s64) inside portable extension blocks.

### Decisive source
```rust
// serializer.rs:3-8 — the whole point, stated by the authors:
// Keeping inline values and borrowed slices as distinct chunks lets the
// serializer reserve for the complete stream once, then bulk-copy each slice.
// Flattening the same chain to `Iterator<Item = u8>` loses those slice
// boundaries and makes `Vec::extend` copy the payload one byte at a time.
// :145-152 — the trust-but-verify close:
if writer.written != encoded_len { return Err(log_buffer_len_mismatch()); }
unsafe { self.set_len(new_len); }
```
The writer is a raw-pointer cursor over space reserved by `try_reserve(encoded_len)`; every `copy_from_slice` re-checks capacity with checked_add (:99-104), so a lying `encoded_len` fails CLOSED with the buffer unchanged — pinned by `chunk_length_mismatch_does_not_change_buffer` (:811-829: a chunk claiming len 0 but writing 1 byte errors AND leaves `[2]` intact). `insert(offset, value)` composes write-then-`rotate_right` to splice at an offset (:224-236); portable extension records are spliced the same way after a pre-computed length check (:238-286).

**Flow:** caller builds a chain via `log_write!(ser, [tag, flags, table_id, SqliteVarint(len), rowid, record], maybe_extension)` → macro `.chain()`s each element's `into_chunks()` → one `write()` → reserve total → per-chunk bulk copy → verify count → set_len. Extension chunks append AFTER the payload when present (the macro's optional-extension arm appends `SqliteVarint(ext.len())` + ext into the SAME stream).

**Invariant:** `encoded_len()` must equal exactly what `copy_to` writes — the design trades one cheap pre-pass for zero mid-write reallocation, and any divergence is a bug surfaced as `log_buffer_len_mismatch`, never silent corruption. Chunks must not overlap the destination buffer (SAFETY comment :105-106).

**Probe:** direct tests in `serializer.rs`: `fragment_chunks_preserve_wire_format` :800-808 (asserts exact bytes `[5, 8, 1, 16, 2, 3]` for a proto payload), `chunk_length_mismatch_does_not_change_buffer` :811-829, `insert_preserves_surrounding_bytes` :832-837, `portable_extension_insert_preserves_wire_format` :840-853. Verified by source inspection at `def9a060`.

**Retrieve:**
```
echo '{"project":"turso","query":"LogChunkStream LogSerializer serialize_op_entry encrypt_payload_in_place","limit":5}' | codebase-memory-mcp cli search_graph
# turso.core.mvcc.persistent_storage.logical_log.serializer.LogSerializer.serialize_op_entry serializer.rs 292-374
```

## Verdict
Adopt the reserve-once/copy-per-chunk shape for any hot serialization path with mixed inline/borrowed fields; keep the post-copy equality assert. Adapt the two-varint split to your compat needs (SqliteVarint only if you must match SQLite's record format byte-for-byte). In-place encryption of the serialized buffer is the companion seam `loglog-encrypted-in-place-expansion`.
