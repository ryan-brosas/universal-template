<!-- capsule-v2 -->
# OAuth refresh lease protocol — how do N processes share one rotating refresh token without double-spending it?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** What is the full acquire→renew→CAS-persist→release choreography for cross-process OAuth refresh, and what does a porter get wrong?

## OAuth refresh lease protocol
**Path/Symbol:** `packages/ai/src/auth-storage.ts:` `AuthStorage.refreshStoredOAuthCredential` (2437–2667); lease hooks declared on `AuthCredentialStore` (:445–448).
**Signature:** `refreshStoredOAuthCredential<T extends OAuthCredential>(provider: string, options: StoredOAuthRefreshOptions<T>): Promise<StoredOAuthRefreshResult<T>>`.
**Data Shape:** Lease = `{owner: uuid, expiresAtMs}`; store methods `tryAcquireCredentialRefreshLease / getCredentialRefreshLeaseExpiresAt / renewCredentialRefreshLease / releaseCredentialRefreshLease`. Constants: LEASE_TTL 15s, POLL 50ms (or min(leaseRemaining,250ms)), RENEW every 5s, OPERATION_TIMEOUT 10s, SKEW 60s.

### Decisive source
```ts
while (hasDurableLease) {
	if (options.signal?.aborted) throw new AIError.AbortError("OAuth refresh ownership aborted by caller");
	// re-list rows EVERY iteration; adopt a peer's fresh copy only when still usable:
	if (
		options.observedCredential &&
		!authCredentialEquals(current, options.observedCredential) &&
		currentIsFresh
	) {
		return { credential: current, refreshed: false, removed: false };
	}
	if (!options.forceRefresh && currentIsFresh) {
		return { credential: current, refreshed: false, removed: false };
	}
	if (this.#store.tryAcquireCredentialRefreshLease?.(row.id, owner, Date.now() + OAUTH_REFRESH_LEASE_TTL_MS)) {
		leasedCredentialId = row.id;
		break;
	}
	const waitMs =
		leaseExpiresAt === undefined
			? OAUTH_REFRESH_LEASE_POLL_MS
			: Math.min(Math.max(leaseExpiresAt - Date.now(), OAUTH_REFRESH_LEASE_POLL_MS), 250);
	await raceCredentialRefreshWithSignal(
		Bun.sleep(waitMs),
		options.signal,
		"OAuth refresh ownership wait aborted by caller",
	);
}
// inside the leased critical section: background renew loop throws ConfigurationError on renewal loss;
// persistence uses tryUpdateAuthCredentialIfMatches(id, serialized.data, merged, {owner, nowMs})
// so a peer rotation that landed mid-refresh WINS the CAS and this process reloads instead of overwriting.
```

**Flow:** poll-loop re-read → freshness short-circuit → lease acquire → re-check guards under lease → refresh with 10s abortable timeout + 5s renewal heartbeat → CAS persist (`tryUpdateAuthCredentialIfMatches`) with lease fence → release in `finally`. Definitive failures CAS-disable via `tryDisableAuthCredentialIfMatches(..., lease)`.
**Invariant:** Refresh tokens that rotate-on-use are never replayed: only the lease owner calls the token endpoint; every persist is conditional on the row still matching the snapshot taken BEFORE the await. A lost CAS ⇒ reload and serve/return the peer's newer credential — never clobber. An expired stored copy is NOT adopted even when a peer rotated (falls through to refresh).
**Probe:** `packages/ai/test/auth-storage-oauth-refresh-race.test.ts` — `does not disable a credential another process already rotated` (:51), `serializes rotating provider refresh tokens across AuthStorage instances` (:394), `does not overwrite a peer rotation after releasing the refresh lease` (:450), `returns the targeted OAuth row after a compare-and-set refresh loss` (:501).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "AuthStorage refreshStoredOAuthCredential", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the poll/renew/CAS/release choreography and all five constants as a unit; adapt the store-side lease implementation to host storage; omit Bun-specifics (`Bun.sleep`, `crypto.randomUUID` is standard). The naive port — refresh-then-unconditional-write — corrupts rows whenever two processes share the SQLite file.
