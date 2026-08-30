<!-- capsule-v2 -->
# Session stickiness & warm-window skip — when does a session reuse its pinned credential instead of re-ranking the pool?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** How is session→credential stickiness persisted, restored after restart, and skipped when the prompt cache goes cold?

## Session stickiness & warm-window skip
**Path/Symbol:** `packages/ai/src/auth-storage.ts:` `#recordSessionCredential` (1958–1983) + `#getSessionCredential` (1986–2032) + `ANTHROPIC_SESSION_STICKY_CACHE_WARM_MS = 60 * 60_000` (:101) + warm-skip gate in `#resolveOAuthSelection` (4830–4862) + `pinSessionOAuthAccount` (5799–5814).
**Signature:** sticky row `{type, index, lastUsedAtMs?}` keyed `provider → sessionId`; persisted under cache key `session:sticky:<provider>:<sessionId>` with 30-day expiry.
**Data Shape:** Persisted JSON `{type, index, credentialId, lastUsedAtMs}` — `credentialId` is the durable anchor; `index` is positional and re-derived on restore.

### Decisive source
```ts
// restore: index is dereferenced through the FULL stored list, never the filtered subset
if (val.credentialId !== undefined) {
	const actualIndex = stored.findIndex(entry => entry.id === val.credentialId);
	if (actualIndex === -1 || stored[actualIndex]?.credential.type !== val.type) {
		this.#store.setCache(cacheKey, "", 0);      // drop unsafe rows
		return undefined;
	}
	val.index = actualIndex;
} else {
	// Fallback: drop unsafe index-only cache rows to prevent wrong-account routing
	this.#store.setCache(cacheKey, "", 0);
	return undefined;
}
// warm skip: Anthropic-only verified boundary
const sessionPreferredIsWarm =
	provider !== "anthropic" ||
	sessionPreferredLastUsedAtMs === undefined ||
	Date.now() - sessionPreferredLastUsedAtMs < ANTHROPIC_SESSION_STICKY_CACHE_WARM_MS; // 1h
const shouldRank = checkUsage && (!sessionPreferredIsAvailable || !sessionPreferredIsWarm || hasPlanRequirement);
```

**Flow:** win ⇒ `#recordSessionCredential` writes in-memory map + durable cache row (backdated `lastUsedAtMs` supported for session-file resume). Next resolve reads sticky first; if available AND warm AND no plan requirement, ranking is skipped entirely and the pinned candidate is hoisted to the front of the round-robin order. When ranking does run, the pin is seeded at position 0 so it wins genuine ties via `orderPos` without overriding a strictly better sibling.
**Invariant:** Sticky indices are only meaningful against the FULL provider array (`[api_key, oauth_A, oauth_B]` — an OAuth-filtered dereference is off-by-N, :2850–2855 comment). Index-only cache rows are destroyed, not trusted. The 1h warm window exists because Anthropic caps OAuth prompt-cache retention (`ttl:"1h"`); other providers keep indefinite stickiness until verified (:93–100). A blocked or plan-ineligible pin always falls through to ranked siblings.
**Probe:** `packages/ai/test/auth-storage-codex-selection.test.ts` — `keeps a Codex session pinned after >1h idle` (:314), `skips expired access-token-only sticky credential and selects fresh sibling` (:2396); `packages/ai/test/auth-storage-oauth-account-select.test.ts` (pin/list surface).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "recordSessionCredential", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt durable-id anchoring + full-list index re-derivation + drop-unsafe-row restore semantics + the warm-window gate shape; adapt the 1h constant to each provider's actual prompt-cache TTL (or leave indefinite); omit Anthropic specifics if the host provider has no prompt-cache economics.
