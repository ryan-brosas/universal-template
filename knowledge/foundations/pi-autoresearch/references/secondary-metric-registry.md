<!-- capsule-v2 -->
# Secondary metric registry — how do optional measurements become schema without a migration?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** How are secondary metrics introduced, completed, and prevented from silently drifting?

## registerSecondaryMetrics + missing/new gate with --force escape
**Path/Symbol:** `harness/server.ts` — register :309–315, call sites :687 (reconstruction) + :318 (updateStateAfterLog); log validation :1254–1274.
**Signature:** `registerSecondaryMetrics(state, metrics)` appends unseen `{name, unit: inferUnit(name)}` preserving first-seen order; validation compares Set(known) vs Set(provided) per log.
**Data Shape:** `secondaryMetrics: MetricDef[]` (`{name, unit}`); per-run `metrics: Record<string, number>`.

### Decisive source
```ts
if (state.secondaryMetrics.length > 0 && status !== 'crash') {
  const missing = [...knownNames].filter((n) => !providedNames.has(n));
  if (missing.length > 0) return { text: `❌ Missing secondary metrics: ${missing.join(', ')}\n\nExpected: ...` };
  const newMetrics = [...providedNames].filter((n) => !knownNames.has(n));
  if (newMetrics.length > 0 && !force) {
    return { text: `❌ New secondary metric(s) not previously tracked: ${newMetrics.join(', ')}\n\nUse --force to add.` };
  }
}
```

**Flow:** first benchmark prints extra METRIC lines → parsed → registered with inferred units on log → thereafter every non-crash log must supply ALL known names (exact-set match). New names require explicit `--force` (schema growth is deliberate); missing names are hard errors (schema shrink is a bug signal); crash logs exempt because metrics may be unmeasurable. Baselines for deltas come from the segment's FIRST run's metrics map, with per-metric fallback to first occurrence in-segment (`findBaselineSecondary` :23–47).
**Invariant:** exact-set equality between consecutive logs keeps time-series columns aligned in every table/scatter render; silent addition would create phantom null columns, silent omission would shift deltas. Order preservation of registration drives column order in the dashboard. Re-init clears the registry together with the baseline (same reset block).
**Probe:** anchors: `grep -c registerSecondaryMetrics harness/server.ts` → 3 lines (:309 def, :318 updateStateAfterLog, :687 reconstruction); `grep -n 'Use --force to add' harness/server.ts | cut -d: -f1` → exactly :1270; direct test coverage via utils.test 'findBaselineMetric/currentResults' + jsonl.test reconstruction registering metrics from replayed lines.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "registerSecondaryMetrics inferUnit force missing secondary", limit: 10 });
```

## Verdict
Adopt exact-set validation with explicit-force growth verbatim; adapt the error channel (CLI text here) to your tooling; omit unit inference if your host has no display layer. Coverage caveat: the force/missing branch itself lacks a dedicated vitest — source-pinned.
