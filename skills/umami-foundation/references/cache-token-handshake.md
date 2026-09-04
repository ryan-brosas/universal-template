<!-- capsule-v2 -->
# Cache-token session handshake — how does an anonymous tracker script get a server-side session without a login?

**Source:** umami v3.3.1 / MIT @ master`ca661c7057984aa98ed4f7083d84dae2f65bfcb0`; Codebase Memory `ext-umami`. **Question:** How does the collect endpoint bootstrap a session for cookieless, unauthenticated browsers and keep repeat hits cheap?

## cache-token-handshake
**Path/Symbol:** `src/app/api/send/route.ts:POST` (cache check :96-119, token mint :355-361); `src/tracker/index.ts:send` (:394-425).
**Signature:** `createToken({ websiteId, sessionId, visitId, iat, sessionLinkId, type: CACHE_TOKEN_TYPE }, secret()) -> string`; response `{ cache, sessionId, visitId }`.
**Data Shape:** JWT signed with `secret()` = sha512(`APP_SECRET` || `DATABASE_URL`) — no separate key. Tracker stores only the opaque `cache` string and echoes it back in the `x-umami-cache` header on every subsequent hit.

### Decisive source
```ts
if (cacheHeader) {
  const result = await parseToken(cacheHeader, secret());
  if (result?.type === CACHE_TOKEN_TYPE) {   // type-tagged: share tokens etc. rejected
    cache = result;
  }
}
...
const token = createToken(
  { websiteId, sessionId, visitId, iat, sessionLinkId, type: CACHE_TOKEN_TYPE },
  secret(),
);
return json({ cache: token, sessionId, visitId });
```

**Flow:** first POST → website lookup → session/visit ids derived from salts → mint cache JWT → return; later POSTs carry `x-umami-cache`, server trusts its `websiteId`/`sessionId`/`visitId`/`iat` WITHOUT re-fetching the website (`if (!cache?.websiteId)` guard) and re-mints a fresh token each response.
**Invariant:** every response re-issues the token (rolling iat); the type discriminator check is what stops the `/api/share` token (signed with the SAME secret) being replayed as a collect cache. A porter who drops `type === CACHE_TOKEN_TYPE` opens cross-token replay.
**Probe:** `grep -c "test(" src/lib/session.test.ts` → 3; id stability pinned by :7 'keeps session IDs stable on the same device'; header round-trip observable at `src/tracker/index.ts:400` (`'x-umami-cache': cache`)
**Probe:** `grep -n "keeps session IDs stable" src/lib/session.test.ts` → :7.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "parseToken createToken CACHE_TOKEN_TYPE send", limit: 10 });
```

## Verdict
Adopt the stateless rolling cache-JWT pattern for any high-volume anonymous ingest API (skip DB reads on cached identity); adapt secret derivation to your own key management (do NOT copy sha512-of-DATABASE_URL if you can avoid it); omit the specific header names.
