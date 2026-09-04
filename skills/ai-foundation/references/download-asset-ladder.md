<!-- capsule-v2 -->
# Download asset ladder — what does a single URL download owe its caller in error handling, size limiting, and socket hygiene?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** When you wrap `fetchWithValidatedRedirects` + `readResponseWithSizeLimit` into one `download()` entry point, which cleanup and error-classification steps can you NOT skip without leaking sockets or misclassifying failures?

## download entry point
**Path/Symbol:** `packages/ai/src/util/download/download.ts:download` (:22-73); factory `create-download.ts:createDownload` (:10-13).
**Signature:** `download({url: URL, maxBytes?: number, abortSignal?: AbortSignal}): Promise<{data: Uint8Array, mediaType: string | undefined}>`; `createDownload(options?: {maxBytes?: number})` returns that function pre-bound (default doc comment says 100 MiB at this layer; `DEFAULT_MAX_DOWNLOAD_SIZE` lives in provider-utils).
**Data Shape:** Returns `{data, mediaType}` where `mediaType` is read from the FINAL response's `content-type` header (`?? undefined`). All failures are normalized to `DownloadError`: non-ok statuses carry `statusCode`/`statusText`; everything else wraps the original as `cause`.

### Decisive source
```ts
if (!response.ok) {
  // Release the connection before rejecting so an error status from an
  // attacker-controlled origin cannot leak open sockets.
  await cancelResponseBody(response);
  throw new DownloadError({ url: urlText, statusCode: response.status, statusText: response.statusText });
}
const data = await readResponseWithSizeLimit({
  response, url: urlText,
  maxBytes: maxBytes ?? DEFAULT_MAX_DOWNLOAD_SIZE,
});
return { data, mediaType: response.headers.get('content-type') ?? undefined };
```
```ts
} catch (error) {
  if (DownloadError.isInstance(error)) throw error;   // already classified — rethrow as-is
  throw new DownloadError({ url: urlText, cause: error });  // network/abort/etc. wrapped
}
```

**Flow:** build UA-suffixed headers once (`withUserAgentSuffix({}, 'ai-sdk/<VERSION>', getRuntimeEnvironmentUserAgent())`) → `fetchWithValidatedRedirects` (SSRF guard, see ssrf-download-guard.md) → non-ok ⇒ **cancel body BEFORE throwing** → `readResponseWithSizeLimit` (Content-Length early-reject + streamed count, both cancel the body on violation) → return bytes + content-type.
**Invariant:** Every terminal path releases the response body — an unconsumed body on a non-ok or oversized response keeps the TCP socket open (both branches are test-pinned). Error classification is single-flavored: callers only ever see `DownloadError` (use `DownloadError.isInstance`, not instanceof chains). The user-agent suffix is applied even to an empty header bag so every egress request identifies the SDK + runtime.
**Probe:** `packages/ai/src/util/download/download.test.ts:276` ("should cancel the body on non-ok response (prevents socket leak)" asserts `onCancel` fired), `:301` (Content-Length > limit cancels body), `:243` (404 ⇒ DownloadError carrying statusCode/statusText), `:263` (fetch rejection ⇒ wrapped DownloadError), `:234` (inline `data:` URLs decode without fetch).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"download cancelResponseBody readResponseWithSizeLimit DEFAULT_MAX_DOWNLOAD_SIZE","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the cancel-body-before-reject discipline and the two-tier Content-Length/streamed size check verbatim — they are security-relevant against attacker-controlled origins; adapt the default max-bytes policy per product surface (transcription/video use `createDownload` overrides); omit the runtime-environment UA segment if your host has no equivalent convention. Direct tests exist and pin all four failure paths at this HEAD.
