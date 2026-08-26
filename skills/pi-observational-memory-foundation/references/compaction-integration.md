<!-- capsule-v2 -->
# Compaction integration — summary replacement with empty-summary decline, and the settled-event proactive trigger

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** How do you make compaction instant, memory-bearing, and safe against the host's auto-retry? *(Trigger half rewritten at pass 3 [DONE:347]: the retryable-error heuristic was DELETED upstream when the trigger moved to `agent_settled`; see settled-event-trigger.md for the full lesson.)*

## Compaction hook (`src/hooks/compaction-hook.ts`)
**Path/Symbol:** `compaction-hook.ts:19-59` (`registerCompactionHook`; empty-summary decline :42-45).
**Signature:** `pi.on("session_before_compact", async (event, ctx) => ({ compaction: {...} }) | { cancel: true } | undefined)`.
**Data Shape:** event carries `preparation.firstKeptEntryId` + `tokensBefore` and `branchEntries`; returned `details` is the validated `MemoryDetails` snapshot (`om.folded`, version 1).

### Decisive source
```ts
if (runtime.compactHookInFlight) { ...; return { cancel: true }; }   // duplicate compaction ⇒ cancel
runtime.compactHookInFlight = true;
try {
	const { preparation, branchEntries } = event;
	const { firstKeptEntryId, tokensBefore } = preparation;
	const projection = buildCompactionProjection(branchEntries as Entry[], firstKeptEntryId,
		{ observationsPoolMaxTokens: observationsPoolMaxTokens(runtime) });
	const summary = renderSummary(projection.reflections, projection.observations);
	if (summary.length === 0) {
		// Decline ownership so Pi's native summarizer preserves the pre-cut context.
		return;                                                        // NEW at ce9fc982
	}
	return { compaction: { summary, firstKeptEntryId, tokensBefore, details: projection.details } };
} finally { runtime.compactHookInFlight = false; }
```

**Flow:** host asks for a summary → hook REPLACES the LLM-summarization with a pure ledger render (`renderSummary`: usage instructions + reflections + observations sections, each line carrying its memory id) → attaches the fold snapshot as structured details → returns synchronously.
**Invariant:** No model call in the hot path — "when compaction happens, you should barely notice." The id-carrying lines are what make `recall(<id>)` work later. THREE distinct outcomes must not be conflated: `{cancel:true}` (duplicate in flight), `undefined` (decline ownership — native summarizer preserves the pre-cut context; returning "" as a replacement would truncate context to nothing), `{compaction}` (full replacement). Duplicate concurrent compactions are cancelled loudly.

## Proactive trigger (`src/hooks/compaction-trigger.ts`) — now on agent_settled
**Path/Symbol:** `compaction-trigger.ts:6-77` (`registerCompactionTrigger`). The old `RETRYABLE_ERROR_RE` (:5-7 pre-drift) and last-assistant-message scan are GONE.
**Signature:** `pi.on("agent_settled", (_event, ctx) => ...)` → threshold check on raw tokens since last compaction → deferred `ctx.compact`.
**Data Shape:** threshold via `resolveCompactAfterTokens(config, contextWindow)` — `"calibrated"` static 81k or `"ratio"` floor(window × 0.68).

### Decisive source
```ts
// Pi emits agent_settled only after retries, automatic compaction, and queued
// continuation have finished, so retry policy stays owned by Pi.
pi.on("agent_settled", (_event, ctx) => {
```
```ts
runtime.compactInFlight = true;
setTimeout(() => {
	if (!ctx.isIdle()) { runtime.compactInFlight = false; /* deferred — agent busy */ return; }
	const currentProgress = rawTokensSinceLastCompaction(currentEntries);
	if (currentProgress < threshold) { runtime.compactInFlight = false; /* another compaction ran */ return; }
	ctx.compact({ onComplete: () => { runtime.compactInFlight = false; }, onError: ... });
}, 0);
```

**Flow:** agent_settled → passive/in-flight guards → raw-token progress ≥ threshold? → capture ctx fields SYNCHRONOUSLY (setTimeout outlives ctx lifetime) → defer to macrotask → re-check idle AND re-check progress (another compaction may have run) → compact ("Compaction cancelled" errors stay silent — already notified).
**Invariant:** Retry safety is now OWNED BY THE HOST's settled event rather than a ~30-alternative regex over error messages — that heuristic was deleted upstream (was: "Pi emits agent_end before its own retry check, so we must detect this ourselves"). Every early-exit path resets `compactInFlight`; the post-timeout re-validation makes stale triggers harmless. The threshold mode ("calibrated" vs context-window "ratio") exists so a 1M-window model isn't preempted at an 81k threshold.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "registerCompactionHook registerCompactionTrigger agent_settled resolveCompactAfterTokens renderSummary buildCompactionProjection", limit: 10 });
```
(Direct tests: `tests/compaction-hook.test.ts` — 7 tests incl. three decline-ownership pins; `tests/compaction-trigger.test.ts` — 24 tests, registration asserted on `"agent_settled"`, retry-suppression test deleted; `tests/session-ledger-render-summary.test.ts`.)

## Verdict
Adopt pure-render summary replacement with id-tagged lines + structured fold details, duplicate-compaction cancellation, EMPTY-SUMMARY DECLINE back to the native summarizer, synchronous ctx capture + deferred idle/progress re-validation, and calibrated-vs-ratio thresholds. Adapt event names to your lifecycle; prefer your host's settled/post-lifecycle event over re-implementing retry detection. Omit the clipboard/status commands if unneeded.
