<!-- capsule-v2 -->
# Encryption page format — where do nonce and tag physically live in an encrypted page, and how is page 1 kept SQLite-header-shaped?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How are whole pages encrypted without changing the page's on-disk size, and what does the reader need before it can even find the cipher?

## Reserved-bytes budget + trailing nonce; header swap with AEAD-bound integrity

**Path/Symbol:** `core/storage/encryption.rs` — `CipherMode` metadata table :413-543 (`nonce_size` :480, `tag_size` :495, `metadata_size = nonce+tag` :510, stable `cipher_id` byte 1..8 :515-528), `EncryptionContext::required_reserved_bytes` :627-629, `encrypt_page` :729-775, `decrypt_page` :778-816, `encrypt_page_1` :819-889, `decrypt_page_1` :892-937, Turso header create/validate :668-726 (`TURSO_HEADER_PREFIX=b"Turso"`, VERSION_OFFSET=5, CIPHER_OFFSET=6, TURSO_HEADER_SIZE=16).
**Signature:** `pub fn encrypt_page(&self, page: &[u8], page_id: usize) -> Result<Vec<u8>>`; `decrypt_page(&self, encrypted_page: &[u8], page_id: usize) -> Result<Vec<u8>>`.
**Data Shape:** every cipher's `metadata_size()` (e.g. AES-GCM: 12B nonce + 16B tag = 28) must equal the DB's per-page reserved-bytes budget — the b-tree layer must never write into the tail of a page.

### Decisive source
```rust
// encrypt_page :742-774 — the size-preserving layout:
let reserved_bytes = &page[self.page_size - metadata_size..];   // must be all-zero (debug assert)
let payload = &page[..self.page_size - metadata_size];
let (encrypted, nonce) = self.encrypt_raw(payload)?;            // ciphertext len == payload len
// result layout: [ciphertext (page_size - nonce_size)] [nonce (nonce_size)]  → exactly page_size
```
Page 1 is special (:852-856 comment): bytes 0-15 become the Turso magic header (`Turso` + version + cipher-id + zero padding), bytes 16-100 stay PLAINTEXT (unencrypted remainder of the 100-byte SQLite database header), bytes 100-end are encrypted, and "the header (the first 100 bytes) as associated data" binds the plaintext header fields into the AEAD tag — decrypt validates `validate_turso_header` (prefix/version/cipher-id match/reserved-zeros, :685-726) and uses "the header on disk … as associated data for protection against tampering" (:910-913), then rebuilds the standard `SQLite format 3\0` prefix in memory (:923-927).

**Flow:** open encrypted DB → read first 16 bytes → `from_cipher_id` selects the mode BEFORE any key material matters → wrong key/mode fails at `decrypt_raw` tag verification. Normal pages round-trip at constant `page_size`: reserved region carries nothing on disk (it exists so payload+nonce fit), nonce trails the ciphertext, tag is stored inside the reserved budget.

**Invariant:** page size NEVER changes under encryption — the layout is `[ciphertext | nonce]` filling exactly `page_size`, made possible by declaring `metadata_size` as reserved bytes up front (this is the contract `page-transform-codec-stack`'s "declared reserved bytes" refers to concretely). Page 1's plaintext header fields are integrity-protected via associated data, not confidentiality. The debug-only zero-check on reserved bytes exists to prove the b-tree layer isn't leaking writes into crypto territory (:839-850).

**Probe:** direct tests in `core/mvcc/database/tests.rs`: `test_mvcc_encrypted_restart_without_key_fails_before_recovery` :15083 (no key ⇒ fail before recovery), `test_mvcc_late_encryption_setup_keeps_metadata_bootstrapped` :15045, plus round-trips in `encryption.rs` test module. Verified by source inspection at `def9a060`.

**Retrieve:**
```
echo '{"project":"turso","query":"EncryptionContext encrypt_page decrypt_page CipherMode","limit":4}' | codebase-memory-mcp cli search_graph
# turso.core.storage.encryption.EncryptionContext.encrypt_page encryption.rs 1036-1040
# turso.core.storage.encryption.EncryptionContext.decrypt_page_1 encryption.rs 892-937
```

## Verdict
Adopt reserved-bytes-as-crypto-budget and the trailing-nonce constant-size page layout; adopt header-swap + header-as-AAD for any format that must stay recognizable/unencrypted-at-the-front while its body is sealed. Adapt cipher table freely — only the `cipher_id` byte stability and metadata_size accounting are load-bearing. Chunked (multi-block payload) encryption of LOG records is a different seam: see `loglog-serializer-chunk-streams` and `logical-log-portable-sync`.
