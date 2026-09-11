<!-- capsule-v2 -->
# Usage report cache & failure cooldown — what does a usage poll serve when the upstream endpoint fails or is rate-limited?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** What are the cache key identity rules, TTL/jitter, and the null-vs-last-good failure contract?

## Usage report cache & failure cooldown
**Path/Symbol:** `packages/ai/src/auth-storage.ts:` `#fetchUsageCached` (3350–3403) + `#fetchUsageUncached` (3244–3349) + `AuthStorageUsageCache.set` durable-expiry trick (:1218–1223) + `#buildUsageCacheIdentity` (3022–3048) + constants (:679–698).
**Signature:** key = `` `report:<[version:]provider>:<baseUrl|default>:<identity>` ``; identity = `type|account:…|email:…|org:…|project:…|enterprise:…`, falling back to a secret hash ONLY when no stable identifier exists.
**Data Shape:** Cache entries `{value: UsageReport|null, expiresAt}`; TTL 5min (`USAGE_REPORT_TTL_MS` from sqlite-credential-store) with ±25% jitter; failure cooldown 10s ±25%; last-good retention 24h.

### Decisive source
```ts
const ttlJitter = USAGE_REPORT_TTL_MS * (Math.random() * 0.5 - 0.25);
if (report !== null) {
	// stagger per-credential expiry so accounts don't refresh in the same window —
	// Anthropic/OpenAI rate-limit /usage per source IP; synchronized fan-out trips 429s.
	this.#usageCache.set(cacheKey, { value: report, expiresAt: Date.now() + USAGE_REPORT_TTL_MS + ttlJitter });
	...
}
// Failure: short jittered cool-down; most providers serve the LAST GOOD value...
const retainLastGood =
	!forceRefresh && this.#resolveUsageProvider(request.provider)?.retainLastGoodOnFailure !== false;
const lastGood = retainLastGood
	? (this.#usageCache.getStale<UsageReport | null>(cacheKey)?.value ?? null)
	: null;
this.#usageCache.set(cacheKey, { value: lastGood, expiresAt: coolDown });
```

**Flow:** fresh hit ⇒ return value as-is (including a cached null); miss ⇒ single-flight via `#usageRequestInFlight` keyed `cacheKey\0epoch`; epoch bumps on every invalidation so stale in-flight results are dropped by the epoch check inside the promise. Definitive failures (401/403 from the provider, definitive OAuth refresh failure on an already-expired token) PURGE the cached value (`{value:null, expiresAt:0}`) instead of cooling down — a revoked credential must not keep rendering stale quota. The cache wrapper writes `value===null` rows with the ORIGINAL expiry but non-null rows get `max(expiresAt, now+24h)` so stale reads (`getStale`) can serve last-good for a day.
**Invariant:** Nulls are data: a cached `null` IS the failure signal and replays until its cooldown expires. Force-refresh skips the fresh read AND the last-good retention. Per-provider cache-key VERSION overrides (`anthropic: 3` etc., :699–711) are the migration mechanism for identity-shape changes.
**Probe:** `packages/ai/test/auth-storage-usage-cache.test.ts` — `caches a successful report and replays it on a second poll` (:216), `serves last-good value through a failure cycle` (:274), `does not replay last-good quota after an explicit invalidation` (:330), `writes per-credential cache TTLs with ±25% jitter so refreshes decorrelate` (:593), `cold-fetches instead of replaying a report stored under the previous Anthropic cache version` (:234).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "fetchUsageCached", limit: 10 });
```

## Verdict
Adopt identity-key composition, jittered TTL, single-flight+epoch invalidation, and the retain-vs-purge failure taxonomy; adapt TTL/cooldown magnitudes; omit provider version-override table contents (host-specific history). Serving stale quota after a 401 is the classic wrong port.
