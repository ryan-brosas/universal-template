<!-- capsule-v2 -->
# Uploaded-file memo cache — how do you avoid re-uploading conversation images when payloads are rebuilt every turn?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** Agent hosts rebuild request payloads from session context on every turn; a naive uploader re-POSTs every historical image each turn — what is the memo key, bound, and scope?

## Uploaded-file memo cache
**Path/Symbol:** `src/payload.ts:194-225` (`MAX_UPLOADED_FILE_CACHE_ENTRIES`, `uploadedFileCache`, `uploadedFileCacheKey`, `rememberUploadedFile`, `clearKimiUploadedFileCache`); consumed at `applyKimiPayloadMutations:483-491` and both transform walkers.
**Signature:** `uploadedFileCacheKey(cacheScope: string, mimeType: string, data: string): string`; `rememberUploadedFile(cache: Map<string,string>, cacheKey: string, url: string): void`.
**Data Shape:** module-level `Map<string,string>` of content-hash → vendor file URL, bounded at 512 entries.

### Decisive source
```ts
// Successful uploads are remembered in a module-level cache shared across
// requests: payloads are rebuilt from session context every request, so
// without it a conversation's images would re-upload on every turn. Keys are
// content hashes rather than the data URLs themselves so the cache does not
// retain every image's base64 payload in memory. Failures are not cached and
// retry on the next request.
const MAX_UPLOADED_FILE_CACHE_ENTRIES = 512;
...
return createHash("sha256")
  .update(cacheScope)
  .update("\0")
  .update(mimeType)
  .update("\0")
  .update(data)
  .digest("hex");
```
```ts
if (
  uploadCache === uploadedFileCache &&
  !uploadCache.has(cacheKey) &&
  uploadCache.size >= MAX_UPLOADED_FILE_CACHE_ENTRIES
) {
  const oldest = uploadCache.keys().next().value;
  if (oldest !== undefined) uploadCache.delete(oldest);
}
```

**Flow:** transform finds a base64 block → compute sha256 over `scope \0 mime \0 base64-data` → hit ⇒ substitute cached URL without calling the uploader → miss ⇒ await upload, remember only on success. Scope selection in the orchestrator: `ctx.uploadCacheScope ? sharedModuleCache : new Map()` with scope defaulting to `"request"`; streamSimpleKimi builds scope as `` `${getBaseUrl(wireProtocol)}:${apiKey}` `` (stream.ts:302) so different accounts/endpoints never share file ids.
**Invariant:** The cache never stores base64 bodies (hash-only keys); eviction applies only to the shared cache (per-request maps are throwaway); failed uploads stay uncached so they retry next turn; identical bytes under different scopes are distinct entries.

**Probe:** `tests/payload.test.ts:274-356` — line 274 pins one upload across two requests returning the same `ms://persisted` for OpenAI blocks; 300 pins the same for Anthropic `source.type:"url"` rewrites; 329 pins two uploads when only the cache scope differs.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "rememberUploadedFile uploadedFileCacheKey cache", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt hash-keyed, bounded, scope-partitioned upload memos keyed by (account-scope, media type, content) — the pattern ports to any host that rebuilds payloads from history. Adapt the scope composition (baseUrl+apiKey here) and entry bound to your memory budget. Omit the FIFO-eviction subtlety only if your host guarantees single-account use. No coverage caveat at this pin.
