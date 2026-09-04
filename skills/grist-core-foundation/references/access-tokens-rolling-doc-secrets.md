<!-- capsule-v2 -->
# AccessTokens rolling doc secrets — how do 15-minute JWTs stay verifiable across worker restarts when the signing secret itself rotates?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What is the secret-lifecycle contract that lets a token signed yesterday-hour verify tomorrow-minute, and why are read and write caches separate?

## Per-doc secret LISTS (max 3), sign with head / verify against all; refresh-and-retry once on verification failure
**Path/Symbol:** `app/server/lib/AccessTokens.ts` — `Deps` (:10–14: `TOKEN_TTL_MSECS = 15*60*1000`, `MAX_SECRETS_KEPT = 3`), `AccessTokens.sign/verify` (:105–134), `_getOrCreateSecret` (:187–201), `_verifyWithGivenDoc` (:142–156), store twins (:224–268).
**Signature:** `sign(content: AccessTokenInfo): Promise<string>` (JWT HS-signed with per-doc secret, `expiresIn: dtMsec/1000.0`); `verify(token): Promise<AccessTokenInfo>`; store: `getSigners(docId)/setSigners(docId, secrets[], ttlMsec)`.
**Data Shape:** Secret list = `string[]`, newest FIRST (`unshift(mint)` then `splice(MAX_SECRETS_KEPT)`); minted as `makeId() + makeId()`. Stores: redis `SETEX token-doc-decoder-<docId> <ttl> <"s1,s2,s3">` (comma-joined!) or in-memory `MapWithTTL`. Cache TTLs = `TOKEN_TTL_MSECS * factor * 0.5` with default factor 10 → caches outlive tokens ~5×; store TTL = full `factor × TTL`.

### Decisive source
```ts
// AccessTokens.ts:187-201 — write path under a PER-DOC mutex
return this._mutex.runExclusive(docId, async () => {
  let secrets = this._writes.get(docId);
  if (secrets && secrets.length >= 1) { return secrets[0]; }        // sign with most recent
  secrets = await this._store.getSigners(docId);
  secrets.unshift(this._mintSecret());                              // newest first
  secrets.splice(Deps.MAX_SECRETS_KEPT);                            // cap at 3
  this._writes.set(docId, secrets);
  await this._store.setSigners(docId, secrets, this._dtMsec * this._factor);
  return secrets[0];
});
// AccessTokens.ts:126-133 — read path: try cached, on ANY failure refresh from store and retry ONCE
try {
  return await this._verifyWithGivenDoc(docId, token);
} catch (e) {
  await this._refreshSecrets(docId);
  return await this._verifyWithGivenDoc(docId, token);
}
```

**Flow:** sign = per-doc KeyedMutex critical section → local `_writes` cache hit returns head → else pull list from store, prepend fresh secret, truncate to 3, persist with full-factor TTL → JWT embeds `{userId, docId, ...options}` + built-in expiry. Verify = untrusted `jwt.decode` first to EXTRACT docId (non-object or missing docId ⇒ 401 "Broken token") → try every cached secret; "Token has expired" ABORTS the ladder immediately (no point trying other secrets — expiry is secret-independent) → any other failure triggers one store-refresh + retry → final failure 401 "Cannot verify token".
**Invariant:** Read and write caches are SEPARATE MapWithTTLs ("kept separate so we don't have to reason about interactions", :56–59) — a signer never invalidates a verifier's view. Overall secret lifetime ≈ `factor × TOKEN_TTL_MSECS × MAX_SECRETS_KEPT` while tokens live 15 min, so secrets never linger orders-of-magnitude beyond the tokens they sign (:68–78 comment). The in-memory store keeps a STATIC module-level map with refcount so multiple instances share keys and close() clears only at zero refs — but a restarted process loses them by design (documented limitation :223).
**Probe:** `test/server/lib/AccessTokens.ts` (:71 "honors access tokens" end-to-end mint+use; attribution suites :145/:171/:192 pin userId propagation through ACL + audit logs). Source pins: `grep -c 'MAX_SECRETS_KEPT' app/server/lib/AccessTokens.ts` = 4; `grep -c 'token-doc-decoder' app/server/lib/AccessTokens.ts` = 1.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"AccessTokens sign verify getSigners setSigners TOKEN_TTL","limit":10,"detail":"ids"}'
```

## Verdict
Adopt rolling-secret-list signing with head-sign/verify-all, the decode→docId→verify order, single refresh-retry, and expired-token short-circuit; adapt store choice (any shared KV replaces redis; comma-join encoding must become list-safe if secrets can contain commas — makeId output is alphanumeric today); omit grist's AccessTokenInfo field set. Direct mocha coverage at this pin; runner-blocked locally — probes recorded as source-pinned assertions.
