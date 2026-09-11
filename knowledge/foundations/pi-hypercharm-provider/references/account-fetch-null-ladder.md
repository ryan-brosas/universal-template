<!-- capsule-v2 -->
# fetchJsonGet null-or-data ladder + single-flight credits + one-shot meta — what does every status API call owe the UI when the network says no?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider` (node `pi-hypercharm-provider.fetchJsonGet`, `index.ts:634-647`). **Question:** Three different status endpoints feed one footer — how do you keep their failure modes from ever corrupting displayed state or stacking concurrent calls?

## Never-throw account fetching with per-endpoint latching
**Path/Symbol:** `index.ts:623-695` — `CREDITS_MIN_INTERVAL_MS = 15_000` (:623) and `ACCOUNT_FETCH_TIMEOUT_MS = 8_000` (:624); `statusAbort`/`statusEpoch`/`lastCreditsFetchAt`/`creditsInFlight`/`metaFetched` :626-632; `fetchJsonGet` :634-647; `refreshCredits` :650-669 (single-flight via `creditsInFlight` :631, throttle stamp `lastCreditsFetchAt` :630); `refreshAccountMeta` :671-695 (`metaFetched` latch :632).
**Signature:** `fetchJsonGet(url: string, apiKey: string | undefined, signal?: AbortSignal): Promise<any | null>`; `refreshCredits(apiKey, signal, force: boolean): Promise<void>`; `refreshAccountMeta(apiKey, signal?: AbortSignal): Promise<void>`.
**Data Shape:** all three funnel into module-singleton `account {balance, teamName, rate, authDaysLeft}` — writes are guarded field assignments, never wholesale replacement mid-session.

### Decisive source
```ts
async function fetchJsonGet(url, apiKey, signal?) {
	try {
		const response = await fetch(url, {
			headers: { Authorization: `Bearer ${apiKey}` },
			signal: signal
				? AbortSignal.any([AbortSignal.timeout(ACCOUNT_FETCH_TIMEOUT_MS), signal])
				: AbortSignal.timeout(8s),
		});
		if (!response.ok) return null;
		return await response.json();
	} catch { return null; }
}
```
```ts
// refreshCredits: stamp-then-check ordering is load-bearing
if (!apiKey) return resolve();
if (!force && Date.now() - lastCreditsFetchAt < 15_000) return resolve();
lastCreditsFetchAt = Date.now();          // stamped BEFORE the await — no herd
if (creditsInFlight) return creditsInFlight;
creditsInFlight = (async () => {
	try { ...account.balance = balance; } finally { creditsInFlight = null; }
})();
return creditsInFlight;
```

**Flow:** `/credits` → balance only; `/teams` → first item's name; `/devices` → match `Pi (<hostname>)` by exact name to read OAuth expiry in days (`Math.max(0, ceil((expMs-now)/86_400_000))`) — skipped silently for API-key auth since that endpoint lists OAuth sessions only. `/hypercharm-status refresh` and turning the account widget on both set `metaFetched = false` before refetching.
**Invariant:** fetchJsonGet NEVER throws — HTTP≠2xx returns `null`, network/timeout/abort all collapse into the same `null`; callers branch on `null` instead of try/catch. Every call composes its session-scoped AbortSignal with a hard 8s timeout via `AbortSignal.any([timeout, signal])`. Balance/team/days write ONLY on type-checked finite values (`Number.isFinite`, non-empty trimmed string, valid date parse) so a malformed payload leaves prior state standing. `metaFetched` latches once-per-session but ONLY when something was actually learned (`teamName !== null || authDaysLeft !== null`) — an all-null response retries next trigger; `refreshCredits` stamps `lastCreditsFetchAt` BEFORE awaiting and collapses concurrent callers onto one promise cleared in `finally`. The balance this ladder writes is always a REPLACEMENT (`account.balance = ...`) — which is precisely what makes optimistic-balance-deduction.md safe.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-hypercharm-provider && grep -c "AbortSignal.any\|AbortSignal.timeout" index.ts'` → 3; `grep -c creditsInFlight index.ts` → 5; `grep -c "metaFetched = false" index.ts` → 4. Runtime path untested upstream — coverage caveat recorded. (Counts re-verified at HEAD 4520704.)
**Coverage caveat:** no upstream tests exercise these paths; smoke suite covers display layer only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "fetchJsonGet refreshCredits", limit: 3 });
```

## Verdict
Adopt the never-throw null-ladder, timeout composition, stamp-then-await single-flight, and learn-only latching as-is. Adapt endpoint shapes and hostname matching to your product. Omit hyper.charm.land URLs.
