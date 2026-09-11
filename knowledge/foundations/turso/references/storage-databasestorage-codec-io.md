<!-- capsule-v2 -->
# DatabaseStorage codec-wrapped completions — how do you decrypt/verify pages AFTER async IO without a second copy on the hot path?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** Page transforms (encryption/checksum) run on completion callbacks — what buffer does the raw read land in, and which errors must never reach the file layer?

## IOContext-selected transform wraps the caller's Completion with a scratch-buffer read
**Path/Symbol:** `core/storage/database.rs`: `trait DatabaseStorage` (:106-133 incl. bootstrap-only `read_header` :107-112), `IOContext` (:17-89: page_transform accessor, `get_reserved_space_bytes` :30-36, `reset_checksum` :84-88), `DatabaseFile::read_page` codec arm (:161-226), checksum arm (:227-267), passthrough (:268), `write_page`/`write_pages` encode-first (:272-336), `encode_buffer` (:362-372).
**Signature:** `fn read_page(&self, page_idx: usize, io_ctx: &IOContext, c: Completion) -> Result<Completion>`; decode callback `FnOnce(Result<(Arc<Buffer>, i32), CompletionError>) -> Option<CompletionError>`.
**Data Shape:** codec reads go into `Buffer::new_temporary(len)` scratch; on success the callback decodes IN PLACE into the ORIGINAL completion's buffer (`decode_page(ctx, buf.as_slice(), original_buf.as_mut_slice())`) and completes it with the transport byte count. Checksums verify against the SAME buffer they read into (`verify_checksum(buf.as_mut_slice(), page_idx)`).

### Decisive source
```rust
// database.rs:107-111 — why read_header exists:
//   /// Reads the encoded prefix of page 1 without applying a page transform.
//   /// This is only for bootstrapping the page layout before a complete page
//   /// can be read and decoded.
// database.rs:179-197 — the error taxonomy inside the wrapped completion:
//   if bytes_read == 0 { original_c.complete(bytes_read); … }        // absent page: NOT an error, skip decode
//   if bytes_read as usize != expected {
//       original_c.error(CompletionError::ShortRead { page_idx, expected, actual });
// database.rs:212-215 + 255-257 — single-failure rule:
//   turso_assert!(!original_c.failed(), "Original completion already has an error");
```
Write side is synchronous-encode-before-submit: `encode_buffer` allocates a fresh temporary and fails BEFORE any pwrite is queued (test pins `writes_submitted == 0` on codec failure). Offsets are overflow-checked `(page_idx - 1) * size` and sizes are asserted power-of-two 512..=65536 on every path.

**Flow:** read: IOContext picks Codec | Checksum | None → None passes the caller's completion straight through → otherwise pread into scratch → wrapped callback verifies/decodes → completes (or errors) the ORIGINAL completion exactly once. Write: assert geometry → encode/checksum into fresh buffer → pwrite/pwritev.

**Invariant:** at most one terminal transition on the original completion (asserted); a zero-byte read completes successfully WITHOUT decoding (absent page ≠ corruption); reserved-space budgets flow from the transform via `get_reserved_space_bytes()` so b-tree layouts stay codec-consistent.

**Probe:** in-file unit tests `page_codec_read_decodes_into_original_database_buffer` (:528), `page_codec_zero_byte_read_reaches_original_completion` (:554, "an absent page must not be decoded"), `page_codec_partial_database_read_fails_before_decode` ShortRead (:591), `page_codec_database_write_error_does_not_submit_io` (:624), `page_codec_database_read_reports_decode_error` (:653), checksum wrapper propagation (:726/:765).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "DatabaseStorage DatabaseFile IOContext encode_buffer read_page write_pages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrap-completion-with-transform pattern and the zero-byte-is-not-an-error rule for any storage medium abstraction with page codecs. Adapt scratch-buffer strategy to your allocator. Omit read_header bootstrapping if your header config is external to the file. Coverage caveat: tests verified by direct read only (no cargo runner).
