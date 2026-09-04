<!-- capsule-v2 -->
# Logical-log deferred commit — how does an append-only recovery log stage optimistic frames without letting failed writes corrupt the CRC chain?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** When a transaction frame is written to disk before the commit decision is final, what keeps the log's length and checksum chain clean if the commit never happens?

## Two-phase append: stage bytes + pending CRC, then confirm or discard
**Path/Symbol:** `core/mvcc/persistent_storage/logical_log.rs:938-965` (`log_tx_deferred_offset`, `advance_offset_after_success`, `discard_pending_write`), chain-state struct `LogTxFrameInfo` :273-287, frame/recovery contract docs :100-142.
**Signature:** `pub fn log_tx_deferred_offset(&mut self, tx: LogRecord, on_serialization_complete: OnSerializationComplete<'_>) -> Result<(Completion, u64)>` — caller MUST call `advance_offset_after_success(bytes)` after the commit succeeds.
**Data Shape:** returns `(Completion, bytes_written)`; the writer offset and `running_crc` do NOT move yet. `LogTxFrameInfo{logical_start_offset, start_crc32c, end_crc32c}` describes the *pending* chain position; `pending_running_crc` holds the staged value between the two phases. Frame trailer = chained `crc32c(prev_frame_crc, header||payload)` + `END_MAGIC`; first frame seeds from the header salt.

### Decisive source
```rust
// :947-961 — annotated invariant:
#[aristo::intent("the in-memory log offset advances only after the corresponding
frame pwrite has completed durably", ..., verify = "full")]
pub fn advance_offset_after_success(&mut self, bytes: u64) { ... }
// :963-966 — abort path:
/// Discard the pending running CRC staged by a deferred write whose
/// two-phase commit aborted before the offset advanced. ... no later write
/// chains its running CRC from a value staged for a write that never confirmed.
```
Recovery mirrors the same discipline (:125-142): torn/incomplete tail accepted as EOF; first invalid frame ends the scan; only header corruption fails closed; replay applies validated frames with `commit_ts > persistent_tx_ts_max` and **restores the writer offset to `last_valid_offset` so torn-tail bytes are overwritten** on the next append.

**Flow:** serialize frame (staged start/end CRC) → pwrite → commit resolves ⇒ `advance_offset_after_success` promotes offset + pending CRC into the live chain | abort/failure ⇒ `discard_pending_write`, next frame chains from the last CONFIRMED end CRC.
**Invariant:** the log's visible length and its CRC chain advance only for confirmed commits — a failed write must leave zero residue in BOTH, or every subsequent frame inherits an unverifiable chain.
**Probe:** in-file tests (module at :3744+): `test_logical_log_torn_tail_stops_cleanly`, `test_crc_chain_invalidates_suffix_on_corruption`, `test_logical_log_corrupt_tail_keeps_valid_prefix`, `test_on_serialization_complete_gets_shared_write_bytes`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "log_tx_deferred_offset advance_offset_after_success discard_pending_write", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt stage→confirm/discard appends for any self-chaining log (CRC or LSN chain). Adapt the confirmation hook to your completion model. Omit encrypted-chunk framing until at-rest crypto is required. Coverage caveat: probes are module tests co-located in the same 8k-line file, not a separate suite.
