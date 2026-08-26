<!-- capsule-v2 -->
# Sent-headers reconciliation — what actually went out vs what you prepared, with proxy credentials masked

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** After the request leaves, how do you show users the real wire headers (axios/Node add several) without leaking proxy passwords or double-listing user headers?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/network/sent-headers.ts:getSentHeaders` (:10-45), `applySentHeadersToRequest` (:48-62).
**Signature:** `getSentHeaders(clientRequest?: ClientRequest) → Record<string,string>; applySentHeadersToRequest(request?, response?) → void`.
**Data Shape:** reads Node's private `clientRequest._header` string (the serialized request block) — NOT `getHeaders()`, which omits wire-added headers like `Connection`; output merged into `request.headers` with user entries winning.

### Decisive source
```ts
/** The proxy agent injects this credential and the user never authored it, so the header
 *  stays visible but its value never is, in the timeline or in `request.headers`. */
sentHeaders[name] = name.toLowerCase() === 'proxy-authorization'
  ? MASK_CHAR.repeat(value.length)
  : value;
```
```ts
// copies the missing ones in. It never replaces a header the user set, ignoring casing
const existing = new Set(Object.keys(request.headers).map((name) => name.toLowerCase()));
Object.entries(response.sentHeaders).forEach(([key, value]) => {
  if (!existing.has(key.toLowerCase())) sentHeaders[key] = value;
});
request.headers = { ...sentHeaders, ...request.headers };
```

**Flow:** split `_header` on CRLF → skip request line (i=1) → parse `name:value` only when colon index > 0 (blank lines / nameless junk skipped; colons INSIDE values survive because slice uses first-colon) → mask `proxy-authorization` value length-preserving → merge into prepared headers as UNDERSPREAD (spread order `{...sentHeaders, ...request.headers}` keeps user casing+value authoritative).
**Invariant:** masking is by lowercased name and preserves LENGTH (UI alignment without disclosure); merge is case-insensitive-additive — never replace, or a declared `user-agent` and sent `User-Agent` become two entries; reading `_header` is deliberately version-fragile private API (comment says why it's the only truthful source).
**Probe:** `packages/bruno-requests/src/network/sent-headers.spec.ts` :1-97 — live http.Server round-trip pins mixed-case preservation, colons-in-values (`Bearer: abc:def`), Host/Connection presence that getHeaders() misses.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "getSentHeaders _header", limit: 5 });
```

## Verdict
Adopt `_header`-block parsing, first-colon splitting, proxy-auth length-masking, additive case-insensitive merge. Adapt if your stack exposes a sanctioned sent-headers API; omit Bruno's timeline wording. Coverage caveat: none — clean coverage at pin.
