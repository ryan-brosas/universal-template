<!-- capsule-v2 -->
# Member eligibility cooldown gate — who is eligible right now, and when does a cooled-down member return?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** How do you track rate-limited accounts so they self-heal after a cooldown without timers or background jobs?

## Lazy cooldown expiry on read, auth first
**Path/Symbol:** `extensions/multi-sub.ts`: PoolState `cooldownMs` default (2139-2162), `PoolManager.getAvailableMembers` (2206-2221), `PoolManager.isMemberExhausted` (2223-2232), `PoolManager.markExhausted` (2396-2401).
**Signature:** `getAvailableMembers(pool: PoolConfig, authStorage: { hasAuth(provider: string): boolean }): string[]`; `isMemberExhausted(pool: PoolConfig, provider: string): boolean`; `markExhausted(providerName: string): void`.
**Data Shape:** per-pool PoolState {exhausted: Map<provider, exhaustedAtEpochMs>, cooldownMs = 5 * 60 * 1000}; eligibility = authenticated AND not (exhausted within cooldown window).

### Decisive source
```ts
getAvailableMembers(pool, authStorage): string[] {
	const state = this.getOrCreatePoolState(pool.name);
	const now = Date.now();
	return pool.members.filter((member) => {
		if (!authStorage.hasAuth(member)) return false;
		const exhaustedAt = state.exhausted.get(member);
		if (exhaustedAt && now - exhaustedAt < state.cooldownMs) return false;
		if (exhaustedAt && now - exhaustedAt >= state.cooldownMs) {
			state.exhausted.delete(member);
		}
		return true;
	});
}
```
`markExhausted` stores `Date.now()` under the member's pool (`providerToPool` lookup; unknown providers are ignored). `isMemberExhausted` applies the same compare-and-delete lazily.

**Flow:** error marks exhausted-at timestamp -> every later eligibility check compares now - exhaustedAt against cooldownMs -> still inside window = ineligible -> window elapsed = entry DELETED on read (self-healing) -> no timers, no sweeper, no persistence.
**Invariant:** auth is checked BEFORE cooldown; cooldown state is keyed per POOL via providerToPool, not globally; expiry is computed from timestamps at READ time, so restarts or clock jumps degrade to "eligible again" rather than stuck; marking exhaustion never throws on unknown providers.
**Probe:** `node tests/runtime-failover-check.mjs --pool-only --failure-path` (harness twin pins exhausted-member skipping and failure paths; green at b9d9d1d7a092).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "getAvailableMembers isMemberExhausted markExhausted cooldown", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt timestamp-based lazy cooldown with delete-on-read — it needs no scheduler and survives crashes gracefully. Adapt the 5-minute default and per-pool keying to your host's retry budget. Omit the authStorage interface coupling; substitute your own credential-presence check.