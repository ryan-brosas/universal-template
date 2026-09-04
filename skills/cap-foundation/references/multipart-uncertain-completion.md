<!-- capsule-v2 -->
# multipart-uncertain-completion — How do you retry a multipart upload's completion call so an interrupted confirmation never double-fails a finished upload?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** When the complete call fails after a transient error, why must a 4xx surface as UNCERTAIN rather than clean failure, and what are the timeout/backoff constants?

## Complete retries 4× on network/5xx with 1s→8s backoff; ANY definitive rejection after a transient becomes MultipartCompletionUncertainError
**Path/Symbol:** `packages/recorder-core/src/instant-mp4-uploader.ts:14-17` (`MAX_COMPLETE_ATTEMPTS=4`, `COMPLETE_RETRY_BASE_DELAY_MS=1_000`, `COMPLETE_RETRY_MAX_DELAY_MS=8_000`), `:31-34` (`COMPLETE_REQUEST_TIMEOUT_MS = 5 * 60 * 1000`), logic `:221-281` (`completeMultipartUpload`).
**Signature:** `async function completeMultipartUpload(videoId, uploadId, parts, meta, api, shouldAbort = () => false): Promise<{ processingStarted: boolean }>`.
**Data Shape:** Parts sorted by partNumber; response `{success, processingStarted?}`; `processingStarted !== false` normalizes to true (missing field ⇒ started).

### Decisive source
```ts
if (error instanceof HttpRequestError && error.status < 500) {
    // A definitive rejection on the first attempt is a real failure.
    // After a transient failure it can equally mean an earlier attempt
    // completed server-side (e.g. the multipart session is gone), so
    // it must surface as uncertain rather than as a clean error.
    if (!sawTransientFailure) { throw error; }
    throw new MultipartCompletionUncertainError(error);
}
sawTransientFailure = true;
if (attempt >= MAX_COMPLETE_ATTEMPTS || shouldAbort()) {
    throw new MultipartCompletionUncertainError(error);
}
```

**Flow:** The completion call is "the one request whose loss can strand a finished upload": JSON control-plane calls all ride `AbortSignal.timeout` (60s default, 5min for complete because server-side assembly scales with part count). Retry ladder only for network errors and 5xx; exhaustion or cancellation also lands in Uncertain. Callers treat Uncertain as "verify state server-side", NOT as cleanup-triggering failure.
**Invariant:** First-attempt 4xx = real error; post-transient 4xx = ambiguous (server may have completed) — conflating them either abandons uploaded bytes or duplicates sessions. All control-plane requests MUST be timed or a hung presign wedges its part until the overflow guard kills the recording.
**Probe:** `packages/recorder-core/__tests__/instant-recording-uploader.test.ts` — `treats interrupted multipart completion as uncertain instead of fatal cleanup` (:649), `keeps finalize successful when server-side processing has not started yet` (:596).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "completeMultipartUpload MultipartCompletionUncertainError", limit: 10 });
```

## Verdict
Adopt the transient-then-definitive uncertainty rule and per-call timeouts. Adapt routes/errors to your API.
