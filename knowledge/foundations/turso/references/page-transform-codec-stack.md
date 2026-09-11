<!-- capsule-v2 -->
# Page transform stack — where do page encryption, checksums, and SQLite's reserved bytes meet without breaking page-1 bootstrap?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How do you encrypt/checksum fixed-size database pages while page 1 must stay decodable before the codec configuration is even known?

## Codec trait with reserved-tail budget + header-as-associated-data for page 1
**Path/Symbol:** `core/storage/page_transform.rs:93-115` (`trait PageCodec`: `codec_id`, `bootstrap_page_info`, `required_reserved_bytes`, `encode_page`/`decode_page`), `PageTransform` enum :200-207, `PageCodecContext{page_no, location}` :44-56; `core/storage/encryption.rs:729/:819` (`encrypt_page`, `encrypt_page_1`, header-as-AD at :855-858); `core/storage/checksum.rs:4-7,81` (8-byte XxHash3_64 tail).
**Signature:** `fn encode_page(&self, context: PageCodecContext, input: &[u8], output: &mut [u8]) -> Result<()>` — engine supplies an equal-size output buffer; codecs needing per-page metadata MUST store it in reserved bytes.
**Data Shape:** `codec_id: PageCodecId([u8;16])` — stable, NON-secret config identifier retained by the shared `Database` so every reopen of the same file uses an equivalent codec. Checksum variant reserves exactly 8 bytes (`CHECKSUM_REQUIRED_RESERVED_BYTES`); AEGIS-256 reserves 48 (nonce 32 + tag 16).

### Decisive source
```rust
// encryption.rs:47-49 — the page-1 problem:
// we don't encrypt the header but instead use the header data as additional data (AD) for the
// encryption of the rest of the page. This provides us protection against tampering and
// corruption for the unencrypted portion.
// :855-857 — mechanics:
// 3. Remaining bytes (100-end) are encrypted
// 4. The header (the first 100 bytes) as associated data
```
The trait doc pins the contract: "Before decoding page 1, the engine uses `Self::bootstrap_page_info` to discover the physical page size and reserved space" — default reads SQLite's byte-order page size at offsets 16..18 (0xFFFF ⇒ 65536) and reserved-space byte at offset 20 (`page_transform.rs:22-37`); SQLCipher-style codecs that transform those fields must recover the values themselves. `PageLocation::{Database,Wal}` lets one codec behave differently per destination. `Checksum` is deliberately a separate `PageTransform` variant — it "only maintains and verifies bytes in the reserved page tail; it does not transform logical SQLite content."

**Flow:** open → read raw page-1 prefix → `bootstrap_page_info` yields size+reserved → construct codec → all subsequent pages encode/decode through `PageTransform::Codec` with checksum verification layered on the reserved tail.
**Invariant:** reserved-byte budgets are declared by the codec (`required_reserved_bytes`) and consumed from the SAME fixed page size — a codec that writes beyond its declared reservation corrupts the neighbor format silently; unencrypted header bytes are still authenticated via AD.
**Probe:** in-file suites — encryption: `test_page_1_encrypt_decrypt_round_trip_with_ad`, `test_associated_data_validation`, `test_turso_header_corruption_detection`; checksum: feature-gated round-trip/tamper tests in `storage/checksum.rs` (`mod tests` :94+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "PageCodec required_reserved_bytes bootstrap_page_info EncryptionContext", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the codec-trait + declared-reservation pattern for any transparent-at-rest layer over a fixed-record file format. Adapt cipher selection (AEGIS vs AES-GCM both self-verifying). Omit multi-cipher variants until needed. Coverage caveat: probes are module tests inside the storage crate, not a standalone suite.
