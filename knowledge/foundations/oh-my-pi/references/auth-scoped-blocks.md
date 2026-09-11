<!-- capsule-v2 -->
# Scoped credential blocks & corruption latch — how do rate-limit backoffs persist across processes without a broken SQLite taking auth down?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** How are temporary usage-limit blocks stored in memory vs SQLite, how do scopes compose, and what happens when the block store corrupts?

## Scoped credential blocks & corruption latch
**Path/Symbol:** `packages/ai/src/auth-storage.ts:` `AuthStorage.#markCredentialBlocked` (1881–1921) + `#getCredentialBlockedUntil` (1825–1868) + `#persistedBlockStoreDamaged` latch (:1307–1315, `#reportDamagedBlockStore` 1943–1951) + scope key `#toScopedBackoffKey` (1759–1761) + probe-after map (:1306).
**Signature:** key = `` `${provider}:${type}` `` unscoped, `` `${provider}:${type}\0${scope}` `` scoped; store row `StoredCredentialBlock {credentialId, providerKey, blockScope /* "" = unscoped */, blockedUntilMs}`.
**Data Shape:** In-memory `Map<backoffKey, Map<credentialIndex, blockedUntilMs>>` + parallel `#credentialBackoffProbeAfter`; persisted via optional store hooks (`getCredentialBlock`, `upsertCredentialBlock` with MAX-on-conflict semantics, `deleteCredentialBlocks`, `cleanExpiredCredentialBlocks`).

### Decisive source
```ts
const nextBlockedUntil = Math.max(existing, blockedUntilMs);      // never shorten a live block
backoffMap.set(credentialIndex, nextBlockedUntil);
probeAfterMap.set(credentialIndex, Math.min(nextBlockedUntil, Date.now() + USAGE_REPORT_TTL_MS));
this.#invalidateUsageReportCache(provider);
```

Reads honour the request's own scopes PLUS the legacy catch-all scope, then take the MAX over in-memory unscoped/scoped and persisted global/scoped rows:

```ts
let blockedUntil = this.#getCredentialBlockedUntilForKey(providerKey, credentialIndex, nowMs);
for (const blockScope of scopes) {
	const scopedBlockedUntil = this.#getCredentialBlockedUntilForKey(
		this.#toScopedBackoffKey(providerKey, blockScope),
		credentialIndex,
		nowMs,
	);
	if (scopedBlockedUntil !== undefined && (blockedUntil === undefined || scopedBlockedUntil > blockedUntil)) {
		blockedUntil = scopedBlockedUntil;
	}
}
const credentialId = this.#getStoredCredentials(provider)[credentialIndex]?.id;
if (credentialId === undefined) return blockedUntil;
const persistedGlobalBlockedUntil = this.#readPersistedCredentialBlock(credentialId, providerKey, "");
if (persistedGlobalBlockedUntil !== undefined && (blockedUntil === undefined || persistedGlobalBlockedUntil > blockedUntil)) {
	blockedUntil = persistedGlobalBlockedUntil;
}
for (const blockScope of scopes) {
	const persistedScopedBlockedUntil = this.#readPersistedCredentialBlock(credentialId, providerKey, blockScope);
	if (persistedScopedBlockedUntil !== undefined && (blockedUntil === undefined || persistedScopedBlockedUntil > blockedUntil)) {
		blockedUntil = persistedScopedBlockedUntil;
	}
}
return blockedUntil;
```

**Flow:** block write updates memory immediately, then best-effort persists to SQLite; reads take the MAX of in-memory unscoped/scoped and persisted unscoped/scoped so a block written before scoping existed still applies. Expired entries are deleted lazily on read. Any SQLite corruption error latches `#persistedBlockStoreDamaged=true` once: every later persisted read/write short-circuits for the process lifetime while in-memory backoff keeps applying — availability over durability, with one loud error naming the repair path (`sqlite3 <path> '.recover'`).
**Invariant:** Blocks are per-SCOPE (e.g. Codex meters `chat` vs `spark`) — judging/healing one meter by another's limits is wrong (`#healCodexUsageBlockScope` :6223–6229 comment). Fresh local or broker-sourced blocks get one usage-cache window before healthy reports may clear them (probe-after), else `/usage` lag instantly erases a just-written 429 block. Sibling-availability checks must consult the SAME scope set selection reads (`siblingBlockScopes`, :4473 comment).
**Probe:** `packages/ai/test/auth-storage-block-persistence.test.ts` — `honors scoped and unscoped blocks written by a previous AuthStorage instance` (:133), `keeps the later expiry when a shorter block is upserted for the same key` (:169), `keeps a block attached to the same credential row after a sibling is disabled` (:257).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "markCredentialBlocked", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-plane (memory+SQLite) blocks with MAX-merge, NUL-scoped keys, legacy catch-all reads, probe-after guard and the corruption latch; adapt scope vocabulary to host meters; omit Codex-specific mirror-row migrations (v4→v7 schema ladder is store-side history).
