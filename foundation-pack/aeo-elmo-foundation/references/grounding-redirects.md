<!-- capsule-v2 -->
# Grounding-redirect resolution — how do you recover real URLs from expiring redirect links?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** When a vendor returns citations as short-lived redirect links with the true domain only in the title, when and how do you rewrite them?

## Resolve-at-fetch, rewrite-in-place
**Path/Symbol:** `packages/lib/src/providers/registry/dataforseo.ts:GROUNDING_REDIRECT_PREFIX` (L200), `resolveGroundingRedirect` (L202–210), `resolveGroundingRedirects` (L212–238).
**Signature:** `resolveGroundingRedirect(url): Promise<string>` (fetch GET, `redirect: "manual"`, 8s AbortSignal, return `location` header if it starts with `"http"` else the original); `resolveGroundingRedirects(raw: unknown): Promise<void>`.
**Data Shape:** walks `raw.tasks[0].result[0].items[].sections[].annotations[]`, collects annotations whose `url` starts with `https://vertexaisearch.cloud.google.com/grounding-api-redirect/`; resolves the UNIQUE url set concurrently into a Map; then mutates each annotation in place.

### Decisive source
```ts
const res = await fetch(url, { method: "GET", redirect: "manual", signal: AbortSignal.timeout(8000) });
const location = res.headers.get("location");
return location?.startsWith("http") ? location : url;   // any failure → original URL
```

**Flow:** runs BEFORE citation extraction inside `runLlmResponse`, so both the stored rawOutput and the extracted citations carry the real source URL/domain. ChatGPT/Perplexity responses contain no redirect URLs so the walk is a cheap no-op for them.
**Invariant:** resolution failures degrade to the original redirect URL — never throw, never drop the citation. The links are short-lived, which is WHY this happens at fetch time rather than read time: wait an hour and every Location header is dead.
**Probe:** `packages/lib/src/providers/registry/dataforseo.test.ts:317` ("resolves Gemini Vertex grounding-redirect citation URLs to the real source") — stubs global fetch returning a `location` header and asserts the fetch was called with `{ redirect: "manual" }`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "resolveGroundingRedirect GROUNDING_REDIRECT_PREFIX annotations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt resolve-once-before-store for any vendor that launders citation URLs through redirects (Google Vertex grounding links today; referrer-paranoid CDNs tomorrow); adapt the prefix constant and payload walk to your vendor's shape; omit nothing — the fail-open fallback and dedup-before-fetch are load-bearing for cost.
