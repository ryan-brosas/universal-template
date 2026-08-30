<!-- capsule-v2 -->
# Consolidation pipeline orchestration — single-flight, cached model resolution, per-phase abort, empty-backoff

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you run three LLM worker stages off session events without ever blocking the agent or double-firing?

## Single-flight trigger (`src/hooks/consolidation-trigger.ts` + `src/runtime.ts`)
**Path/Symbol:** `consolidation-trigger.ts:138-185` (`registerConsolidationTrigger`, `maybeLaunchConsolidation`), `runtime.ts:40-63,91-104`.
**Signature:** `pi.on("agent_start" | "turn_end", launch)` → fire-and-forget `void runtime.launchConsolidationTask(ctx, work)`.
**Data Shape:** Runtime flags: `consolidationInFlight`, `consolidationPhase: "observer"|"reflector"|"dropper"|undefined`, `consolidationPromise`, plus last-error slots per phase.

### Decisive source
```ts
function maybeLaunchConsolidation(pi, runtime, ctx): void {
	runtime.ensureConfig(ctx.cwd);
	if (runtime.config.passive === true) return;
	if (runtime.consolidationInFlight) return;
	const entries = ctx.sessionManager.getBranch() as Entry[];
	if (!anyStageDue(entries, runtime, realContextTokens(ctx))) return;
	...
	void runtime.launchConsolidationTask(ctx, async () => withDebugLogContext({...}, async () => {
		await runConsolidationPipeline(pi, runtime, consolidationCtx);
	}));
}
```
```ts
// runtime.ts — tracked task never rejects into the host
return (async () => {
	let errorMessage: string | undefined;
	try { await work(); } catch (error) {
		errorMessage = error instanceof Error ? error.message : String(error);
		if (hasUI && ui) ui.notify(`Observational memory: ${label} failed: ${errorMessage}`, "warning");
	} finally { onFinally(errorMessage); }
})();
```

**Flow:** event → passive? → in-flight? → any stage due? → snapshot ctx into a plain object (events may outlive the live ctx) → launch async pipeline WITHOUT awaiting. Errors are caught inside the tracked task and surfaced as UI warnings; the promise never rejects.
**Invariant:** Consolidation NEVER blocks or awaits the host loop; the in-flight flag guarantees at most one pipeline at a time (re-entry is a silent no-op); config loads lazily exactly once (`ensureConfig`).

## Phase ladder + cached resolver + empty-backoff
**Path/Symbol:** `consolidation-trigger.ts:187-219` (`runConsolidationPipeline`), `:116-136` (`makeModelResolver`), `:241-253,330-341` (backoff).
**Data Shape:** resolver caches ONE ResolveResult for all three stages of a run; backoff = `{sessionIdentity, coverageId, tokensAtEmpty}`.

### Decisive source
```ts
let cached: ResolveResult | undefined;
return async (stage) => {
	cached ??= await runtime.resolveModel({ ... });
	if (cached.ok) { runtime.resolveFailureNotified = false; return cached; }
	if (!runtime.resolveFailureNotified && ctx.hasUI && ctx.ui) {   // notify ONCE across stages
		ctx.ui.notify(`Observational memory: ${stage} skipped — ${cached.reason}`, "warning");
		runtime.resolveFailureNotified = true;
	}
	return undefined;
};
```
```ts
// Deliberate-empty backoff (#23): an intentional "nothing to record" verdict
// must not re-fire the observer every turn over the same span.
if (sessionIdentity !== backoff.sessionIdentity || coverageId !== backoff.coverageId
	|| tokens >= backoff.tokensAtEmpty + runtime.config.observeAfterTokens) {
	runtime.observerEmptyBackoff = undefined;      // retry allowed
} else { return "continue"; }                      // skip this turn
```

**Flow:** observer → reflector → dropper strictly in order; each stage catches its own errors (recorded to `last*Error` + debug log) and the pipeline RETURNS EARLY on failure/abort — later stages never run on stale data. Model resolution happens ONCE per run and is reused; resolve failures notify once then stay quiet until a success resets the flag. A clean observer "nothing to record" arms the backoff; it clears when the session changes, coverage advances, or another observe-window of tokens arrives. An `ObserverStreamError` (API/stream failure) is NOT a clean empty (#32): it aborts without arming backoff and leaves coverage untouched.
**Invariant:** Distinguish deliberate-empty (routine, arm backoff, keep coverage) from stream-failure (warn, abort, keep coverage so nothing is marked covered). Every exit path leaves coverage markers consistent with what was actually recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "maybeLaunchConsolidation runConsolidationPipeline makeModelResolver launchConsolidationTask observerEmptyBackoff ObserverStreamError", limit: 10 });
```
(Direct tests: `tests/consolidation-trigger.test.ts` (763 lines — trigger gating, phase sequencing), `tests/runtime.test.ts`, `tests/stream-errors.test.ts`.)

## Verdict
Adopt fire-and-forget single-flight scheduling, ctx snapshotting for outliving events, one-resolution-per-run model caching with once-only failure notification, strict phase order with early-return aborts, and the deliberate-empty vs stream-failure distinction with token-window backoff. Adapt event names (`agent_start`/`turn_end`) and UI plumbing to your host. Omit Pi-specific debug-log context wiring if your host lacks structured logging.
