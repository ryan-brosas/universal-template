<!-- capsule-v2 -->
# Streaming Oversize Read Cap — how do you enforce a file-size ceiling on remote reads without buffering first and asking later?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** A registry client fetches arbitrary user-addressed files over HTTP and a CLI subprocess — where exactly must the size limit be enforced so a huge or hostile payload never lands in memory?

## content-length pre-check + cumulative streamed byte counter with cancel
**Path/Symbol:** `packages/shadcn/src/registry/github-cli.ts:readGitHubResponseTextWithLimit` (:71-106), constant `MAX_GITHUB_SOURCE_FILE_SIZE = 5 MiB` (:19); `buildContentsEndpoint` sha re-validation (:276-288); post-hoc gh check (:269-271).
**Signature:** `readGitHubResponseTextWithLimit(response: Response, limit = MAX_GITHUB_SOURCE_FILE_SIZE): Promise<string>`; throws `GitHubTransportError("oversize")`.
**Data Shape:** Three enforcement tiers keyed by what the transport exposes: a `content-length` header (REST), a streamable body (`response.body` reader), or an already-buffered stdout string (`gh` via execa maxBuffer).

### Decisive source
```ts
const contentLength = Number(response.headers.get("content-length"))
if (Number.isFinite(contentLength) && contentLength > limit) {
  throw new GitHubTransportError("oversize")        // tier 1: before reading
}
if (!response.body) {
  const text = await response.text()
  if (Buffer.byteLength(text, "utf8") > limit)
    throw new GitHubTransportError("oversize")      // tier 2b: buffered fallback
  return text
}
const reader = response.body.getReader()
let total = 0
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  total += value.byteLength
  if (total > limit) {
    await reader.cancel()                           // stop the download itself
    throw new GitHubTransportError("oversize")      // tier 2a: mid-stream
  }
  chunks.push(value)
}
```

**Flow:** REST path — header pre-check rejects before any body byte is read; otherwise chunks accumulate under a running total that aborts the stream the moment it crosses 5 MiB. gh path — execa `maxBuffer` bounds the child process and a post-hoc `Buffer.byteLength(stdout)` check re-enforces the same cap on the returned string. Related hard-input gate: `buildContentsEndpoint` validates the sha against `/^[a-fA-F0-9]{40}$/` before interpolating it into any URL (`invalid-response` kind otherwise).
**Invariant:** The oversize failure must be a typed transport error (so guidance can say "must be smaller than 5 MiB"), not a raw abort; the stream must be CANCELLED, not merely abandoned, so the connection stops draining. All three tiers must agree on one constant.
**Probe:** `packages/shadcn/src/registry/github-cli.test.ts` — :330-344 fake Content-Length of 100 MiB rejected as `oversize` without reading; :347-362 within-limit body resolves, streamed body crossing a 10-byte limit rejects. Runner caveat: node_modules absent in checkout — pinned by direct reads.
**Coverage:** github-cli.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "readGitHubResponseTextWithLimit oversize content length stream reader cancel limit", limit: 8 });
// observed: readGitHubResponseTextWithLimit #2 (:71-106) behind an unrelated
// helpers/stream.cancel hit — recorded honest rank
```

## Verdict
Adopt the three-tier ladder (header pre-check → streaming cumulative counter with explicit cancel → buffered post-check) for any client that downloads user-addressed content. Adapt the cap constant and whether you count bytes or characters (count bytes: multibyte UTF-8 defeats .length checks). Omit the gh/maxBuffer tier if you have no subprocess transport.
