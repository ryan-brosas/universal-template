<!-- capsule-v2 -->
# Portable cursor fixed-point — why is the sync cursor encoded by iterating until the frame size stops changing?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How do you publish a byte offset "cursor" inside a payload whose own serialized width changes that offset — without a magic padding constant?

## Iterate frame_end_offset(varint-width of itself) to a fixed point

**Path/Symbol:** `core/mvcc/persistent_storage/logical_log/serializer.rs` — `PortableChangePayload::with_stable_end_offset` :662-723, doc comment :658-661 ("The cursor itself is a varint, so crossing a varint-width boundary changes the frame size that determines the cursor"), `frame_end_offset` closure :667-711 (extension_size → plaintext_size → optional encrypted blob size → prefix+tx-header+body+trailer → write_offset+frame_size), convergence loop :713-722, `PortableEndOffsetCtx { write_offset, includes_log_header, tx_header_size, recovery_payload_size, encrypted_payload_chunk_size, encryption_overhead }` :633-640.
**Signature:** `fn with_stable_end_offset(ctx: PortableEndOffsetCtx, commit_ts: u64, encoded_metadata: &[u8]) -> Result<Self>`.
**Data Shape:** protobuf body: field1 = end_offset (varint), field2 = commit_ts (varint), then raw metadata; record header: type(u16) + flags(u16) + len(u32) (`EXTENSION_RECORD_HEADER_SIZE = 8`, logical_log.rs:352).

### Decisive source
```rust
// serializer.rs:713-722 — the whole algorithm:
let mut end_offset = frame_end_offset(0)?;          // assume empty payload
loop {
    let payload = Self::new(end_offset, commit_ts, encoded_metadata);
    let encoded_len = payload.encoded_len()...;     // how wide is THAT cursor?
    let next_end_offset = frame_end_offset(encoded_len)?;  // recompute with real width
    if next_end_offset == end_offset {
        return Ok(payload);                          // fixed point reached
    }
    end_offset = next_end_offset;
}
```
The self-reference: `end_offset` is stored as a protobuf varint INSIDE the extension record, and its value depends on the total frame size — which includes the varint's own width. A 1-byte→2-byte varint transition shifts every downstream offset. Rather than reserving worst-case widths, the encoder iterates: start from the offset implied by an empty payload, measure the encoding it produces, recompute, stop when measuring no longer moves the value.

**Flow:** writer computes ctx once per log (write_offset, whether header bytes count, tx header size, chunk size, cipher overhead) → `with_stable_end_offset` converges in ≤ a few iterations (varints grow ~every 2^7×k) → `insert_portable_extension` splices the sealed record into the log buffer at a recorded hole (:238-286). Sync readers decode `end_offset` and seek straight to the next recoverable frame boundary without understanding local frame internals.

**Invariant:** NEVER compute the cursor from a guessed/worst-case encoded length — a mismatch between assumed and actual width corrupts the published boundary silently. The loop must terminate on strict equality; monotonic growth guarantees convergence because each iteration either stabilizes or strictly increases the varint width class (finite).

**Probe:** direct tests in `serializer.rs`: `fragment_chunks_preserve_wire_format` :800-808 pins the proto body byte-for-byte (`[5, 8, 1, 16, 2, 3]` = len 5, f1=1, f2=2, metadata `[3]`); integration: `collect_mvcc_portable_change_bytes_with_encryption` + decode round-trip in `core/mvcc/database/tests.rs` :15318/:16170. Verified by source inspection at `def9a060`.

**Retrieve:**
```
echo '{"project":"turso","query":"with_stable_end_offset PortableChangePayload end_offset","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt fixed-point iteration for any self-describing length field whose width feeds back into its own value; adopt the ctx-struct parameterization so the same math serves plain and encrypted frames. Adapt the varint/protobuf skin freely — the pattern is the loop. Version gating of which extensions are emitted is covered in `logical-log-portable-sync`.
