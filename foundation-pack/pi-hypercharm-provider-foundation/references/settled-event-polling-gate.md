<!-- capsule-v2 -->
# agent_settled polling gate + pending-commit turn accounting — which lifecycle events may touch the network, and when does captured usage become visible?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** How do you poll account state so that sessions without your provider's activity make ZERO status API calls, and the balance is still fresh right after each turn?

## Event wiring: session_start / model_select / turn_end / agent_settled / session_shutdown
**Path/Symbol:** `index.ts:1031-1105` (the five `pi.on(...)` registrations), commit logic `index.ts:802-828` (`commitPending`), reset `index.ts:788-799` (`resetStatusState`), credits throttle `index.ts:623-669` (`CREDITS_MIN_INTERVAL_MS = 15_000` :623, `refreshCredits` :650, single-flight via `creditsInFlight`).
**Signature:** `commitPending(ctx: ExtensionContext): void`; `refreshCredits(apiKey, signal, force: boolean): Promise<void>`.
**Data Shape:** module-singleton `sessionStats {requests, spendHc}` + `account {balance, teamName, rate, authDaysLeft}`; per-turn pendings are plain module lets.

### Decisive source
```ts
// agent_settled (not agent_end): fires only when no automatic retry,
// compaction, or queued continuation can follow — the one moment polling
// /v1/credits is both fresh and not redundant. Gated on session activity
// so sessions without HyperCharm turns make zero API calls here.
pi.on("agent_settled", async (_event, ctx) => {
	if (sessionStats.requests > 0 || sessionStats.spendHc > 0) {
		await refreshCredits(cachedApiKey, ..., false);   // throttle-respecting
		if (!metaFetched) await refreshAccountMeta(...);
		updateStatus(ctx);
	}
});
```
And the commit gate:
```ts
function commitPending(ctx) {
	if (!pendingSawUsage && pendingRequests === 0) return;
	sessionStats.requests += pendingRequests;
	sessionStats.spendHc += pendingSpendHc;
	... // zero out pendings; on pendingSawOutOfCredits → forced balance refetch + one-time notify
}
```

**Flow:** `session_start`: bump `statusEpoch`, abort both controllers, reload config, `resetStatusState()`, re-register provider identity, prefetch credits/team ONLY if a HyperCharm model is already active → `model_select`: throttled credits refresh when a HyperCharm model is chosen → `turn_end`: `await settleTeeReaders()` then `commitPending` then retry-once credits fetch if first-turn fetch raced/failed (`:1082-1085`) → `agent_settled`: the only periodic re-poll point, activity-gated (:1092-1100) → `session_shutdown`: abort controllers and clear all three UI slots. Between polls the balance now moves optimistically (see optimistic-balance-deduction.md).
**Invariant:** polling happens at `agent_settled`, never `agent_end` — retries/compaction/queued continuations would make an earlier poll stale AND redundant. The prefetch gating means "sessions that never use the provider make zero status-related API calls" (header comment `:41-43`). `refreshCredits` is throttled to ≥15s unless `force=true`, collapses concurrent callers into ONE promise (`creditsInFlight`), and stamps `lastCreditsFetchAt` BEFORE the await (no thundering herd). `metaFetched` latches account metadata once per session; `/hypercharm-status refresh` resets it.
**Probe:** runtime path untested upstream — deterministic probe: source-read of the five registration blocks confirms no other network-touching code paths exist outside `revalidateModels`/`refresh*`. Coverage caveat recorded.
**Coverage caveat:** event names are pi-runtime API surface (`pi.on`) — port must map to host equivalents.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "agent_settled refreshCredits", limit: 5 });
```

## Verdict
Adopt the settled-event-only polling gate, activity gating, single-flight throttled credits, and pending→commit accounting. Adapt event names/throttle values to your host. Omit hypercharm endpoints.
