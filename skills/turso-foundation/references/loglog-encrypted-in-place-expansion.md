<!-- capsule-v2 -->
# Loglog in-place payload encryption — how do you AEAD-expand a serialized buffer inside itself without a second allocation?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Ciphertext chunks are LARGER than plaintext chunks (each grows by tag+nonce) — how can encryption happen in place, and what binds each chunk's authentication?

## Back-to-front transform: reserve zeroed tail, then encrypt last-chunk-first

**Path/Symbol:** `core/mvcc/persistent_storage/logical_log/serializer.rs` — `LogSerializer::encrypt_payload_in_place` :398-477; sizing helpers in `logical_log.rs`: `ENCRYPTED_PAYLOAD_CHUNK_SIZE = 32 * 1024` :308, `encrypted_payload_chunk_count` :358-364 (`div_ceil`, 0→0), `encrypted_chunk_plaintext_len` :370-386, `encrypted_chunk_blob_size = plaintext+tag+nonce` :389-402, `encrypted_payload_blob_size` :406-427, `build_encrypted_chunk_aad` :429-445; `EncryptedPayload { enc_ctx, payload_start, plaintext_size, chunk_size, salt, op_count, commit_ts }` serializer.rs:785-793.
**Signature:** `pub(crate) fn encrypt_payload_in_place(&mut self, payload: EncryptedPayload<'_>) -> Result<()>`.
**Data Shape:** per 32KiB plaintext chunk the on-disk blob is `plaintext_len + tag + nonce`; AAD is a fixed 32-byte little-endian struct `[salt(8) | payload_size?(8) | op_count(4) | commit_ts(8) | chunk_index(4)]`.

### Decisive source
```rust
// serializer.rs:426-428 — the direction is the invariant:
// Ciphertext chunks are larger than plaintext chunks. Moving and
// encrypting them back-to-front preserves plaintext not yet consumed.
for chunk_index in (0..chunk_count).rev() {
    encrypted_tail -= encrypted_len;
    // copy plaintext chunk to its (later) ciphertext position, then:
    let (ciphertext, tag_and_nonce) = chunk.split_at_mut(plaintext_len);
    let (tag, nonce) = tag_and_nonce.split_at_mut(tag_size);
    payload.enc_ctx.encrypt_chunk_in_place(ciphertext, &aad, tag, nonce)?;
}
turso_assert!(encrypted_tail == 0, ...);   // :468-471 — cursor must land exactly at payload_start
```
The buffer was first grown with `try_resize_zeroed(payload_start + on_disk_size)` (:418) — extra space for all tags/nonces exists BEFORE any copy. The LAST plaintext chunk's AAD carries `Some(total_plaintext_size)` (`(chunk_index + 1 == chunk_count).then_some(plaintext_size)` :446-448); earlier chunks carry None. That trailing total authenticates the whole payload length, so a truncated log tail fails AEAD verification on the final chunk rather than silently replaying a prefix.

**Flow:** serialize ops into buffer → compute `on_disk_size` → resize-zeroed to final size → iterate chunks from LAST to FIRST: shift plaintext forward to its ciphertext offset with `copy_within` (skipped when offsets coincide), encrypt in place writing tag after ciphertext and nonce after tag → assert tail cursor hit exactly payload_start and final length equals on_disk_size.

**Invariant:** process chunks strictly in REVERSE — a forward pass would overwrite not-yet-encrypted plaintext (ciphertext of chunk i overlaps plaintext region of chunk i+k). Every chunk's identity (salt, op_count, commit_ts, index) rides in the AAD, NOT the key stream: same plaintext under a different transaction/context produces different authentication failure modes instead of cross-transaction splicing.

**Probe:** direct tests in `core/mvcc/database/tests.rs`: `test_encrypted_recovery_large_payload_multi_chunk` :15110 (3×chunk_size value survives restart byte-exact), `test_encrypted_recovery_corrupted_later_chunk_keeps_checkpointed_prefix` :15145 (corrupting a later chunk preserves the checkpointed prefix), `test_mvcc_portable_changes_are_encrypted_with_log_body` :16170 (`bytes_contain(log, b"secret-alpha")` must be false). Verified by source inspection at `def9a060`.

**Retrieve:**
```
echo '{"project":"turso","query":"encrypt_payload_in_place EncryptedPayload chunk aad","limit":5}' | codebase-memory-mcp cli search_graph
# turso.core.mvcc.persistent_storage.logical_log.serializer.LogSerializer.encrypt_payload_in_place serializer.rs 398-477
```

## Verdict
Adopt back-to-front in-place expansion for any fixed-region cipher transform where output > input; keep the zeroed-reserve + terminal-cursor assert. Adapt chunk size/AAD layout freely but keep the last-chunk-carries-total-size trick — it converts truncation into an authenticated failure. Constant-size page encryption (no growth) is the different seam `encryption-page-format`.
