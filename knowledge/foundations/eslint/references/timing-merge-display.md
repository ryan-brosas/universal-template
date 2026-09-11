<!-- capsule-v2 -->
# Timing harness merge & display — how does per-rule timing stay zero-cost when off, survive workers, and print a sorted table on exit?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** Beyond the stats envelope (rule-timing-harness capsule), how do the module singleton, worker merge, and exit-hook table actually behave?

## timing.js singleton
**Path/Symbol:** `lib/linter/timing.js:enabled` (:44), `getListSize()` (:53), `display(data)` (:78–129), `time(key, fn, stats)` (:144–163), `getData/mergeData/disableDisplay` (:166–193), exit hook (:194–197).
**Signature:** `time(key, fn, stats?)` — wrapper returning `fn(...)` or `{result, tdiff}`; `mergeData(dataToMerge)` adds foreign totals into process map.
**Data Shape:** `TIMING` env decides everything at require time: falsy ⇒ zero-cost wrappers; `"all"` ⇒ ∞ rows; integer >10 ⇒ that many rows; anything else (incl. "true", "foo", "0", 10) ⇒ MINIMUM_SIZE 10.

### Decisive source
```js
function time(key, fn, stats) {
  return function (...args) {
    const t = startTime(); const result = fn(...args); const tdiff = endTime(t);
    if (enabled) { if (typeof data[key] === "undefined") data[key] = 0; data[key] += tdiff; }
    return stats ? { result, tdiff } : result;
  };
}
if (enabled) process.on("exit", () => { if (displayEnabled && Object.keys(data).length > 0) display(data); });
```

**Flow:** hrtime pair → accumulate into `Object.create(null)` keyed by ruleId → workers call disableDisplay and ship `timing.getData()` in results → main merges (`data[key] += value`) → exit prints sorted-desc table with Relative % column.
**Invariant:** accumulation is keyed ADDITIVE across files AND processes — a rule's total is the sum over every lint of every file in every worker. Display suppression (`disableDisplay` from runWorkers' failure path, or worker contexts) prevents partial tables; the empty-data guard means a TIMING run with zero timed rules prints nothing. getListSize treats non-numeric strings as default-10 (parseInt NaN fails the `>10` check) — "TIMING=all" is case-insensitive. The stats branch returns the envelope WITHOUT suppressing errors: fn throws propagate before tdiff is used.
**Probe:** `tests/lib/linter/timing.js` (:15–58 getListSize env matrix: unset/true/foo/0/1/5/10 ⇒ 10, "11"/"100" passthrough :43–50, "all"/"ALL" ⇒ Infinity :51–57).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "timing time mergeData disableDisplay getListSize", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.timing.time" });
```

## Verdict
Adopt the require-time-enabled + additive-merge + exit-display triad for any cross-process profiling harness; adapt table rendering.
