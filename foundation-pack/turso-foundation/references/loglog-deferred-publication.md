<!-- capsule-v2 -->
# Logical log deferred publication — why does the writer offset lag the pwrite, and what happens to the CRC on abort?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How do I keep a journal's in-memory cursor and checksum chain consistent when commits can abort after bytes hit the page cache?

## log_tx_deferred_offset → advance_offset_after_success / discard_pending_write
**Path/Symbol:** `core/mvcc/persistent_storage/logical_log.rs:log_tx_deferred_offset` (:938-944), `advance_offset_after_success` (:947-956, aristo intent id `aristos:logical_log_inmemory_offset_advances_after_durable_write`), `discard_pending_write` (:963-965), pending field (:589-593).
**Signature:** `log_tx_deferred_offset(tx, on_serialization_complete) -> (Completion, bytes_written)` — writes but does NOT advance the offset; caller must call `advance_offset_after_success(bytes)` only after confirming the commit succeeded. `advance_offset_immediately: true` exists for the checkpoint path.
**Data Shape:** `pending_running_crc: Option<u32>` stages the post-frame chain state; it becomes authoritative ONLY on success.

### Decisive source
```rust
// logical_log.rs:947-956:
pub fn advance_offset_after_success(&mut self, bytes: u64) {
    self.offset = self.offset.checked_add(bytes).expect("logical log offset overflow");
    self.running_crc = self
        .pending_running_crc
        .take()
        .expect("advance_offset_after_success called without pending deferred write");
}
// :963-965 — the abort twin:
// "Discard the pending running CRC staged by a deferred write whose two-phase
//  commit aborted before the offset advanced. This must be called on the abort
//  path so no later write chains its running CRC from a value staged for a
//  write that never confirmed."
```

The doc comment states the porting rationale directly: "The MVCC commit path uses deferred writes so an aborted commit can be silently overwritten; the offset must not advance before confirmation" (test comment :4809-4811). An optional `on_serialization_complete` callback receives shared ownership of framed bytes + `LogTxFrameInfo {logical_start_offset, start_crc32c, end_crc32c}` between framing and the disk write.

**Flow:** frame+pwrite at current offset (offset unchanged) → commit confirms ⇒ advance offset + promote pending CRC; abort ⇒ discard_pending_write, leaving cursor+chain exactly where they were so the torn tail is overwritten by the next frame.
**Invariant:** the in-memory write cursor and running CRC may only advance together, and only after durability confirmation — advancing either early forks the chain from unconfirmed bytes.
**Probe:** `test_logical_log_rowid_negative_varint_roundtrip` (:4811): "deferred write must not advance offset before advance_offset_after_success" (:4852), after which all frames are readable with a valid CRC chain.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "log_tx_deferred_offset advance_offset_after_success", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-method contract verbatim whenever journal appends share fate with a transaction that can abort post-write; adapt naming; omit the immediate-advance path if you have no checkpoint-time writer. Coverage caveat: none material — direct in-file probe.
