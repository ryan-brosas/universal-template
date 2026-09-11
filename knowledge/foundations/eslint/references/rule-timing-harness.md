<!-- capsule-v2 -->
# Rule timing harness — how do you make per-rule profiling opt-in, worker-safe, and mergeable across processes?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you wrap arbitrary rule functions with timing that costs nothing when disabled and aggregates across threads?

## timing module
**Path/Symbol:** `lib/linter/timing.js` (whole file :1–209) — IIFE singleton `time(key, fn, stats)` (:144–160), `getListSize` (:53–69), `display` (:78–129), `getData/mergeData/disableDisplay` (:166–191).
**Signature:** `time(ruleId, fn, stats?) → wrapped(...args)` returning fn's result, or `{result, tdiff}` when `stats:true`; env gate is the string `TIMING`.
**Data Shape:** module-global `data: Record<ruleId, ms>` on a null prototype; display list capped at max(10, parsed TIMING) or ∞ for "all"; per-call stats flow into Linter's `slots.times.passes[]` via `storeTime` (`linter.js:417–438`).

### Decisive source
```js
const enabled = !!process.env.TIMING;              // decided ONCE at require time
function time(key, fn, stats) {
  return function (...args) {
    const t = startTime();
    const result = fn(...args);
    const tdiff = endTime(t);
    if (enabled) { data[key] = (data[key] ?? 0) + tdiff; }
    return stats ? { result, tdiff } : result;
  };
}
if (enabled) {
  process.on("exit", () => { if (displayEnabled && Object.keys(data).length > 0) display(data); });
}
```

**Flow:** runRules wraps `createRuleListeners` AND every listener with `timing.time(ruleId, …)` only when `timing.enabled || stats`; workers call `disableDisplay()` so only the main process prints; parent merges child totals via `mergeData`. `storeTime` buckets by fix-pass index so pass N's parse/fix/rule times stay separable.
**Invariant:** the wrapper must be transparent when disabled — same arity, same return shape unless stats requested; exit-hook printing means data survives process teardown without flush hooks in library code; double-wrapping (stats + TIMING) is handled by the `result/tdiff` envelope, not by conditionals at call sites.
**Probe:** `tests/lib/linter/timing.js` (:15–51 getListSize env parsing) + `tests/lib/eslint/eslint.js` (:10499+ "Use stats option" suite).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "timing storeTime mergeData disableDisplay", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.timing.getListSize" });
```

## Verdict
Adopt the zero-cost-when-disabled wrapper + exit-hook display + merge-across-workers pattern; adapt to your perf API; omit the ASCII table if your host has a profiler UI.
