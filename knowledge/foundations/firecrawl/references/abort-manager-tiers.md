<!-- capsule-v2 -->
# Tiered AbortManager — how do external cancels, scrape timeouts, and engine snipes stay distinguishable?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I fan one cancellation out to N consumers while preserving WHO cancelled and WHY?

## Tiered AbortManager
**Path/Symbol:** `apps/api/src/scraper/scrapeURL/lib/abortManager.ts`:`AbortManager` (:8-124) + `AbortManagerThrownError` (:126-135); consumed at `scrapeURL/index.ts` (:699-706 snipe instance, :780-799 outer timer) and `engines/index.ts` (`scrapeURLWithEngine`).
**Signature:** `new AbortManager(...instances: (AbortInstance|null|undefined)[])`; `.child(...)` → derived manager; `.asSignal(): AbortSignal`; `.throwIfAborted()`; `.scrapeTimeout()/.engineNearestTimeout(): number|undefined`; `.dispose()`.
**Data Shape:** `AbortInstance = { signal: AbortSignal; timesOutAt?: Date; tier: "external" | "scrape" | "engine"; throwable: () => any }`. The tier is the ONLY discriminator the whole pipeline uses to decide fatal vs swallow.

### Decisive source
```ts
private register(abort: AbortInstance) {
  const handler = () => {
    if (!this.mappedController) return;
    const inner = this.resolveInner(abort);              // throwable(); catch => value
    this.mappedController.abort(new AbortManagerThrownError(abort.tier, inner));
  };
  abort.signal.addEventListener("abort", handler);
}
child(...instances) { return new AbortManager(...this.aborts, ...instances.filter(Boolean)); }
asSignal(): AbortSignal { if (!this.mappedController) this._mapController(); return this.mappedController!.signal; }
scrapeTimeout() { // min over tier==="scrape" timesOutAt minus now — undefined when none
  return Math.min(...timeouts.map(x => x.getTime())) - Date.now();
}
```

**Flow:** scrape-level timeout arms an AbortController whose abort reason is `ScrapeJobTimeoutError` (built in buildMetaObject); engine loop creates a per-loop `snipeAbort` (tier `"engine"`, throwable `EngineSnipedError`) shared by every engine attempt via `meta.abort.child(snipeAbort)` and aborted once a winner exists (:932 `snipeAbortController.abort()`), killing all losers. Consumers that accept native signals call `asSignal()`; every abort surfaces as `AbortManagerThrownError(tier, inner)` so callers branch on tier: `tier === "engine"` ⇒ log-and-continue waterfall, otherwise rethrow (index.ts :862-870, :901-909). Error-path unwrapping: the top-level catch converts `AbortManagerThrownError` to its `.inner` before reporting (:1528-1530).
**Invariant:** Listeners are registered LAZILY — only when `asSignal()` is first called — but `throwIfAborted()` polls without listeners, so a manager used purely synchronously never needs a mapped controller. `dispose()` removes every listener; `scrapeURLLoopIter` disposes the CHILD manager in `finally` (:643-645) while the parent survives the whole request — forgetting child disposal leaks a listener per engine attempt.
**Probe:** anchored at repo root `apps/api/src`: `grep -n 'tier === "engine"' scraper/scrapeURL/index.ts` → exactly 2 hits (:863, :902); `grep -n 'snipeAbortController' scraper/scrapeURL/index.ts` → exactly 3 hits (declare :699, instance literal :700-706 block, abort call :932).
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "AbortManager tier child dispose", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tiered-abort pattern (typed instances + wrapper error carrying tier + lazy mapped signal + child managers) for any nested cancellable work; adapt tiers/taxonomy; omit Firecrawl's scrape/engine-specific timeout defaults.
