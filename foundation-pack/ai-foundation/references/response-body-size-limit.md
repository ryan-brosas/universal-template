<!-- capsule-v2 -->
# Response body size limit — how do you turn a potential OOM process kill into a catchable DownloadError?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How is a fetch response body read with an enforced byte ceiling, and why is Content-Length alone not enough?

## readResponseWithSizeLimit
**Path/Symbol:** `packages/provider-utils/src/read-response-with-size-limit.ts:readResponseWithSizeLimit` (:33-102); constant `DEFAULT_MAX_DOWNLOAD_SIZE` (:20).
**Signature:** `readResponseWithSizeLimit({response, url, maxBytes? = 2 * 1024 * 1024 * 1024}): Promise<Uint8Array>`; throws `DownloadError`.
**Data Shape:** Returns concatenated Uint8Array; the 2 GiB default exists because `fetch().arrayBuffer()` has ~2x peak overhead (undici buffers internally, then copies into the JS ArrayBuffer) — over-limit downloads otherwise die with an uncatchable V8 OOM (source comment :15-19).

### Decisive source
```ts
// Early rejection based on Content-Length header:
const contentLength = response.headers.get('content-length');
if (contentLength != null) {
  const length = parseInt(contentLength, 10);
  if (!isNaN(length) && length > maxBytes) {
    await cancelResponseBody(response);   // release the socket BEFORE throwing
    throw new DownloadError({ url, message: `... exceeded maximum size of ${maxBytes} bytes (Content-Length: ${length}).` });
  }
}
const reader = body.getReader(); const chunks = []; let totalBytes = 0;
try {
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    totalBytes += value.length;
    if (totalBytes > maxBytes) throw new DownloadError({ url, message: '... exceeded maximum size ...' });
    chunks.push(value);
  }
} finally {
  try { await reader.cancel(); } catch { /* preserve original rejection */ }
  finally { reader.releaseLock(); }
}
```

**Flow:** Content-Length early check (with body cancel) → incremental streamed read counting every chunk → over-ceiling throw mid-stream → finally-cancel + release-lock → concatenate once at the end.
**Invariant:** The header check is advisory ONLY — servers lie (test :160 "lying Content-Length: says small, sends large"), so the streamed counter is the real enforcement. Cancel errors in the finally are swallowed to PRESERVE the original DownloadError. Missing/zero-length bodies return empty arrays, never throw.
**Probe:** `packages/provider-utils/src/read-response-with-size-limit.test.ts:62` (early header rejection), `:83` (body cancelled on header rejection), `:100/:124` (streamed abort; error preserved when cancel fails), `:160` (lying header), `:230` (exact boundary passes, maxBytes+1 fails).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"readResponseWithSizeLimit DEFAULT_MAX_DOWNLOAD_SIZE cancelResponseBody","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the two-layer enforcement (header fast-path + streamed truth) and the cancel-in-finally discipline verbatim; adapt the 2 GiB default to your heap budget; omit the undici-specific rationale comment. Feeds response-handler-factory (all text/binary reads route through this).
