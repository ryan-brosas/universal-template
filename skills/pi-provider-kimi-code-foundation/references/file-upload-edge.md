<!-- capsule-v2 -->
# File-upload IO edge — how do you recover a media upload from token rotation without failing the request?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** When a vendor's access tokens are short-lived and rotated by peer processes, an upload can 401 mid-session — should the request fail, and when may media stay inline?

## File-upload IO edge
**Path/Symbol:** `src/payload.ts:110-176` (`uploadKimiFile`); helpers `deriveFilesBaseUrl` 71-74, `getUploadFilename` 81-99; injected via `Uploader` type into payload transforms.
**Signature:** `(apiKey: string, mimeType: string, data: string, thresholdBytes?: number, deps?: { fetch?: typeof fetch; refreshAccessToken?: (currentToken: string) => Promise<string | null> }) => Promise<string | null>`.
**Data Shape:** base64 media in, vendor file-reference URL (`ms://<id>`) out; `null` on any failure (caller leaves the block inline rather than dropping the message).

### Decisive source
```ts
const isVideo = mimeType.startsWith("video/");
if (!mimeType.startsWith("image/") && !isVideo) return null;
// The inline threshold applies to images only: the Kimi API has no inline
// video path (upstream kimi-code uploads every video via /files), so videos
// always upload.
if (!isVideo && buffer.length <= threshold) return null;
...
let response = await postUpload(apiKey);
// Kimi access tokens are short-lived and invalidated server-side as soon
// as any peer process rotates them, so a 401 here usually means our key
// snapshot went stale mid-session, not that login is broken. Mirror the
// chat-stream recovery: force one refresh and retry once.
let responseText: string | undefined;
if (response.status === 401) {
  responseText = await response.text();
  const refreshed = await refreshAccessToken(apiKey);
  if (refreshed && refreshed !== apiKey) {
    console.error("[kimi-coding] upload got 401, retrying with refreshed token");
    response = await postUpload(refreshed);
    responseText = undefined;
  }
}
```

**Flow:** reject non-media MIME → compute threshold (arg ?? env `KIMI_CODE_UPLOAD_THRESHOLD_BYTES` ?? 1 MiB) → skip inline-sized images (videos bypass) → POST multipart (`file` + `purpose=image|video`, filename from MIME map) → on 401: drain the stale body, force exactly one token refresh, retry once only when the refreshed token is new → parse `{id}` → return `ms://id`. Any throw is caught, logged, and mapped to `null`.
**Invariant:** At most one refresh+retry per upload, gated on the refreshed token differing from the current one (prevents infinite loops against a stuck store); the unauthorized response body must be consumed before retrying; failure degrades to inline content instead of raising.

**Probe:** `tests/payload.test.ts:792-925` — line 803 pins the retry Authorization sequence `["Bearer old-token", "Bearer new-token"]`; 826 pins `staleResponse.bodyUsed === true`; 843/859 pin no-retry when refresh yields null or the same token; 875 pins purpose=video regardless of threshold; 893/909 pin non-media rejection and non-401 no-refresh.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "uploadKimiFile refresh retry 401", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the ladder: threshold-gated inline vs upload, videos-always-upload policy hook, single difference-gated refresh-retry with body draining, null-on-failure. Adapt endpoint URL derivation (`{base}/files`), MIME→filename map, purpose values, and the refresh callback to your auth stack. Omit the ms:// scheme and Kimi debug logging. Deps-injection of fetch/refresher is the testability seam worth copying. No coverage caveat at this pin.
