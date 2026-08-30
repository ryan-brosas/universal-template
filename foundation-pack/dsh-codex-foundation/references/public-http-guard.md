<!-- capsule-v2 -->
# Public HTTP guard — how do you fetch user-supplied HTTP(S) bytes so DNS-rebind, private-range, metadata, redirect, and size attacks are all rejected before use?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** what does a minimal public-network-only HTTP reader look like when the URL comes from untrusted input but the result bytes feed an agent context?

## Resolve-check-pin fetch loop
**Path/Symbol:** `src/public-http.ts:250-287 fetchPublicHttpResource`, `src/public-http.ts:94-104 isPublicNetworkAddress`, `src/public-http.ts:139-165 collectBoundedBytes`, `src/public-http.ts:167-241 requestPinned/pinnedLookup`, `src/public-http.ts:244-247 NODE_PUBLIC_HTTP_RUNTIME`; constants `PUBLIC_HTTP_HOP_TIMEOUT_MS = 30_000` (13) and `PUBLIC_HTTP_MAX_REDIRECTS = 5` (15).
**Signature:** `fetchPublicHttpResource(source: string, maxBytes: number, signal: AbortSignal, runtime: PublicHttpRuntime = NODE_PUBLIC_HTTP_RUNTIME): Promise<PublicHttpResource>` with `PublicHttpRuntime { resolve(hostname, signal): Promise<readonly ResolvedNetworkAddress[]>; get(url, address, maxBytes, signal): Promise<PublicHttpHop> }`.
**Data Shape:** success is `{ data: Uint8Array, display: finalUrl.href, name?: basename(pathname) }`; a hop is `{ status, location?, data? }` after framing and byte-ceiling enforcement; failure is a thrown `Error` naming the violated boundary. The injectable `PublicHttpRuntime` seam exists precisely so SSRF regressions are testable without sockets.

### Decisive source
```ts
let url = new URL(source)
assertTargetUrl(url)
for (let redirects = 0; ; redirects += 1) {
  if (signal.aborted) throw abortError(signal)
  const addresses = await runtime.resolve(url.hostname, signal)
  if (addresses.length === 0 || addresses.some(candidate => !isPublicNetworkAddress(candidate.address))) {
    throw new Error(`remote image host ${JSON.stringify(url.hostname)} must resolve only to public network addresses`)
  }
  const hop = await runtime.get(url, addresses[0]!, maxBytes, signal)
  if (hop.status >= 300 && hop.status < 400) {
    if (redirects >= PUBLIC_HTTP_MAX_REDIRECTS) { /* throw */ }
    if (hop.location === undefined) { /* throw */ }
    url = new URL(hop.location, url)
    assertTargetUrl(url)
    continue
  }
  // non-2xx/non-3xx → HTTP <status> error; data undefined → no-body error
}
```
Classification invariant (`isPublicNetworkAddress`): strip `[]`/`%`, IPv4 must fall outside the blocked IANA special/local/documentation/multicast/reserved `BlockList`; IPv6 must be inside global unicast `2000::/3` AND outside the blocked special ranges (`::`, ULA fc00::/7, link-local fe80::/10, multicast ff00::/8, TEREDO 2002::/16, doc 2001:db8::/32 …). Anything else — including every non-IP string — is not public.

**Flow:** assert http(s) + no embedded credentials → per hop: fresh DNS resolution → require EVERY resolved address public (a mixed public/private answer is rejected wholesale, never "pick the public one") → pin the checked address into the socket's lookup function so the connection cannot silently resolve elsewhere → enforce declared `Content-Length` AND streamed accumulation against `maxBytes` under a 30 s per-hop timer with abort destroying request+response → on redirect, re-parse `location` against the current URL, re-assert target scheme/credentials, and loop (≤5 hops).
**Invariant:** DNS answers are never cached into trust — each hop re-resolves and re-checks, so a redirect to a cloud-metadata IP (`169.254.169.254`) dies before its socket opens while a legitimate CDN redirect survives with its own freshly pinned address; size limits hold even when the server lies about `Content-Length`; aborts race against connect/read via a settled-once finish guard.
**Probe:** `tests/public-http.spec.ts` (6 tests: classification table incl. `::ffff:127.0.0.1` and `fe80::1` rejected; private DNS answer refused with `runtime.get` NOT called; mixed public/private answer refused; 302-to-metadata refused after exactly one hop while public redirects complete with per-hop pinned addresses asserted on every `get` call; declared-length and streamed byte ceilings both enforced).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.public-http\\.(fetchPublicHttpResource|isPublicNetworkAddress|collectBoundedBytes)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 3, has_more false; `get_code_snippet(fetchPublicHttpResource)` served lines 250-287 matching the pinned checkout.

## Verdict
Adopt the resolve→check-all→pin→bounded-hop→recheck-each-redirect loop, the "every address must be public" rule over first-valid-address, dual declared/streamed size ceilings, and the injectable runtime seam for deterministic tests. Adapt the blocked-range table to your threat model and the consumer-specific bits (image accept header, filename projection). Omit trusting cached resolutions across redirects or honoring redirects past a hard cap. Coverage: `src/public-http.ts` and `tests/public-http.spec.ts` are `no_recorded_issue` + `metadata_match`; the full Vitest suite passed at this pin.
