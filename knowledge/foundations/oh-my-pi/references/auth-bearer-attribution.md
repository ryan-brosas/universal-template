<!-- capsule-v2 -->
# Bearer fingerprint attribution & rotation — how does a delayed usage-limit response find the credential that caused it?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** When a 429 arrives after the OAuth token already rotated, how is the right row blocked?

## Bearer fingerprint attribution & rotation
**Path/Symbol:** `packages/ai/src/auth-storage.ts:` `fingerprintOAuthBearer` (:89–91) + `#oauthBearerFingerprints` map (:1301–1302) + `#recordOAuthBearerCredentialId` (1631–1641) + `#findOAuthCredentialIdForBearer` (1643–1649) + consumption in `markUsageLimitReached` (4510–4522).
**Signature:** `fingerprintOAuthBearer(bearer: string): string` = SHA-256 → base64url; history cap `OAUTH_BEARER_FINGERPRINT_HISTORY_LIMIT = 8` per row.
**Data Shape:** `Map<provider, Map<credentialRowId, string[≤8]>>`; recorded at resolve time (`#tryOAuthCredential` :5482) with the EXACT bytes handed to the request.

### Decisive source
```ts
// SHA-256 bearer fingerprint, so superseded OAuth token bytes never enter the identity cache.
function fingerprintOAuthBearer(bearer: string): string {
	return createHash("sha256").update(bearer).digest("base64url");
}
...
if (!sessionCredential && options?.credentialId === undefined && options?.apiKey !== undefined) {
	// Account quota survives OAuth bearer rotation. Attribute a delayed
	// usage-limit response through the durable row id captured when this
	// exact bearer was resolved; NEVER use this alias for hard auth errors.
	const credentialId = this.#findOAuthCredentialIdForBearer(provider, options.apiKey);
	...
	if (index >= 0) sessionCredential = { type: "oauth", index, explicit: true };
}
```

**Flow:** resolve ⇒ record fingerprint(bytes→row). Later, an out-of-band rate-limit error carrying the old bearer resolves back to the durable row id and blocks THAT row. Rotation cleanup: when a provider's stored list changes, fingerprint histories for vanished row ids are pruned (`#setStoredCredentials` :1613–1622); each row keeps ≤8 fingerprints because a token can rotate mid-flight several times before delayed responses drain.
**Invariant:** Attribution-by-fingerprint is valid ONLY for usage-limit outcomes (quota attaches to the account across rotations); hard auth errors must NOT use it (an old bearer failing auth says nothing about the current row state). Fingerprints are hashes precisely so superseded token bytes are never persisted or compared raw.
**Probe:** `packages/ai/test/usage-attribution.test.ts` + codex-selection suite's `exhausted response headers block the sticky account before the next request` (:2288).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "fingerprintOAuthBearer recordOAuthBearerCredentialId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt hash-fingerprint ledgers with bounded history + usage-limit-only attribution; adapt history depth to host rotation cadence; omit if host has no rotating-token providers. Matching raw bearer substrings is both a security and correctness bug.
