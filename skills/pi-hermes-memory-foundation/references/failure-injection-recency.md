<!-- capsule-v2 -->
# Failure injection recency window — inject the NEWEST N failures (newest-first), not the oldest; zero disables

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** The system prompt carries a capped block of recent failure memories — which end of the age-filtered list survives the cap?

## getSystemPromptInjection failure slice
**Path/Symbol:** `src/store/memory-store.ts` (:557–564 inside system-prompt assembly); constants `DEFAULT_FAILURE_INJECTION_MAX_AGE_DAYS = 7`, `DEFAULT_FAILURE_INJECTION_MAX_ENTRIES = 5` (`src/constants.ts`). One-line change vs pre-wave: `recentFailures.slice(0, maxFailures)` → `maxFailures > 0 ? recentFailures.slice(-maxFailures).reverse() : []`.
**Signature:** internal to `getSystemPromptInjection()`; renders via `renderFailureBlock(failures)` inside a fenced block.
**Data Shape:** `getFailureEntries(maxAgeDays)` returns age-filtered entries OLDEST→NEWEST in file order; the slice takes the LAST `maxFailures` then REVERSES → newest-first display.

### Decisive source
```ts
const maxFailures = this.config.failureInjectionMaxEntries ?? DEFAULT_FAILURE_INJECTION_MAX_ENTRIES;
const recentFailures = this.getFailureEntries(maxAgeDays);
if (recentFailures.length > 0) {
  const failures = maxFailures > 0 ? recentFailures.slice(-maxFailures).reverse() : [];
  …parts.push(this.fenceBlock(this.renderFailureBlock(failures)));
}
```

**Flow:** assemble system prompt → pull failures within the age window → keep the newest N, presented newest-first so the most relevant lesson leads → fence and append. `failureInjectionMaxEntries: 0` yields an empty array (no block) — distinct from `undefined` (default 5).
**Invariant:** a "recent failures" budget that keeps the OLDEST entries under overflow is self-defeating — the pre-wave `slice(0, N)` kept stale lessons and dropped fresh ones exactly when the store grew past the cap; `.slice(-N).reverse()` makes the cap bite at the old end. Zero must mean OFF, not unlimited.
**Probe:** `npx tsx --test tests/store/memory-store.test.ts` — "respects configured failure injection max entries" (:931), "injects no failure memories when max entries is zero" (:947), "respects configured failure injection max age days" (:957). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "renderFailureBlock getFailureEntries failureInjectionMaxEntries", limit: 5 })`

## Verdict
Adopt newest-first recency windows for any prompt-injected memory class with a count cap. Adapt ages/caps. Pair with `memory-store.md` (entry format) and `standing-instructions.md` (the other injected block with its own budget).
