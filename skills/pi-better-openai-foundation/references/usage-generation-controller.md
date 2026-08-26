<!-- capsule-v2 -->
# Generation-guarded refresh controller — how do you run a periodic fetch loop that survives stale contexts, coalesces concurrent requests, and shuts down cleanly?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What is the polling-controller contract (single-flight + queued latest-writer + generation invalidation + stale-context detection) for extension status widgets?

## UsageController
**Path/Symbol:** `src/usage-controller.ts:class UsageController` (:45-304); single-flight queue :157-168, :226-239; generation guard :120-138; throttle :187-193; lifecycle :252-303.
**Signature:** `start(ctx)/shutdown()/restartAfterSettingsChange(ctx,cfg)/refresh(ctx, modelId?, options?, generation?)`.
**Data Shape:** State: snapshot + updatedAt + error + lastFetchAt; `sessionGeneration` monotonic token; `queuedUsageRefresh` slot.

### Decisive source
```ts
if (this.usageRefreshInFlight) {
  const queued = this.queuedUsageRefresh?.generation === this.sessionGeneration
    ? this.queuedUsageRefresh : undefined;
  this.queuedUsageRefresh = { ctx, generation, modelId: resolvedModelId,
    notify: queued?.notify || options?.notify, force: queued?.force || options?.force };
  return;
}
...
} finally {
  this.usageRefreshInFlight = false;
  const next = this.queuedUsageRefresh;
  this.queuedUsageRefresh = undefined;
  if (next && !this.shuttingDown && next.generation === this.sessionGeneration)
    void this.refresh(next.ctx, next.modelId, {...}, next.generation);   // exactly one replay
}

private isStale(error) => error.message.includes("This extension ctx is stale");
// → deactivateGeneration(generation): bump generation, drop queue, abort in-flight, stop timer
```
`start()` bumps generation FIRST (`++this.sessionGeneration`) so in-flight refreshes from the previous session fail the currency check at every await boundary (:120-122, :146, :173, :200). Throttle: silent non-forced refreshes within `refreshIntervalMs` of lastFetch are skipped — but the timestamp is stamped BEFORE the fetch so overlapping timers don't double-fire (:193). Status display adds a "stale <countdown>" suffix when now-updatedAt exceeds 2× interval (:95-98).

**Flow:** session_start → start() (new generation, force-refresh, unref'd interval) → each tick: currency check → throttle → fetch under merged [ctx-signal, 10s timeout, controller-abort] signals → apply or record error → finally: release flag and replay AT MOST ONE queued request.
**Invariant:** Every async continuation re-validates `generation === sessionGeneration && !shuttingDown` before touching state — stale contexts can never write snapshots after restart/shutdown; the queue holds only the LATEST request with OR-merged notify/force flags; settings changes go through `restartAfterSettingsChange`, never raw timer mutation.
**Probe:** direct UsageController suite absent upstream at this pin — behavior is pinned indirectly via footer integration (`tests/footer.test.ts`) and the exported `_test` surface; caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "UsageController refresh queuedUsageRefresh sessionGeneration", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt generation-token lifecycle + single-flight-with-latest-slot + pre-fetch throttle stamping. Adapt the fetch body (here ChatGPT usage endpoint via `requestCodexUsage`). Omit pi ExtensionContext coupling.
