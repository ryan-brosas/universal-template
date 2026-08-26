<!-- capsule-v2 -->
# Benchmark adapter normalization — one uniform snapshot schema over heterogeneous benchmark artifacts

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you normalize different benchmarks' native artifacts (per-trial dirs vs result JSON vs JSONL records) into ONE queryable run/trace schema without hard-coding benchmark semantics into storage or UI?

## Metric definitions + per-kind readers + declared-not-derived metrics
**Path/Symbol:** `packages/metaharness/src/benchmarks.ts`:`BenchmarkDefinition`/`BENCHMARK_DEFINITIONS` (7-45), `readEditSnapshot` (146-190), `readSnapcompactSnapshot` (192-240), `readBenchmarkSnapshot` dispatch (242-273).
**Signature:** `readBenchmarkSnapshot(benchmark: BenchmarkKind, jobDir: string): BenchmarkSnapshot`; `interface BenchmarkDefinition { kind; label; metrics: MetricDefinition[] }` with `MetricDefinition { key; label; format: "percent"|"number"|"usd"; higherIsBetter }`.
**Data Shape:** uniform `BenchmarkSnapshot = { traces: BenchmarkTrace[]; total; done; pass; fail; error; running; costUsd; tokIn; tokOut; tokCache; score: number|null; metrics: Record<string, number|null> }`. Each trace: `{name, task, status, reward, costUsd, durationMs, detail, tracePath}` where `tracePath` is an adapter-owned LOCATOR (`result.dump/<task>/run-1.md`, `record:<lineNumber>`, `<trial>/agent/omp.txt`) resolved later by the server.

### Decisive source
```ts
export const BENCHMARK_DEFINITIONS: BenchmarkDefinition[] = [
    { kind: "harbor", label: "Harbor", metrics:
        [{ key: "success_rate", label: "Success rate", format: "percent", higherIsBetter: true }] },
    { kind: "edit", label: "TypeScript edit", metrics: [
        { key: "task_success_rate", ... }, { key: "edit_success_rate", ... }] },
    { kind: "snapcompact", label: "SnapCompact", metrics:
        [{ key: "f1", ... }, { key: "exact_match", ... }] },
];
// edit: one trace per ATTEMPT — name `${task.id}__${runIndex+1}` keeps attempts distinct
status: run.success ? "pass" : run.error ? "error" : "fail",
tracePath: path.join("result.dump", task.id.replace(/[^a-zA-Z0-9._-]/g, "_"), `run-${runNumber}.md`),
running: Math.max(0, result.summary.totalRuns - traces.length), // scheduled-but-unwritten
```

**Flow:** store/server call `readBenchmarkSnapshot(kind, jobDir)` → dispatch to the kind's reader: harbor walks trial directories + authoritative job-level `result.json` totals; edit flattens `result.json`'s tasks×runs into per-attempt traces (error beats fail when `run.error` is set); snapcompact parses `records.jsonl` lines into per-record traces with `record:N` locators and derives weighted F1/EM from `summary.json` rows (Σ f1·n / Σ n) → every reader returns the same snapshot shape with `metrics` keyed by that adapter's DECLARED definitions and `score` = its primary headline metric.
**Invariant:** storage and UI never hard-code benchmark semantics — they render whatever `BENCHMARK_DEFINITIONS` declares (the `/api/benchmarks` endpoint serves the definitions themselves). Trace names must distinguish attempts of one task (`task__N`). Missing artifacts ⇒ a zeroed empty snapshot, never a throw. `metrics` values are computed by the adapter's own formula (weighted by sample count for snapcompact), not re-derived downstream.
**Probe:** `packages/metaharness/test/benchmarks.test.ts:19-85` — `normalizes edit attempts, traces, tokens, and declared metrics` (trace name/path shape), `normalizes SnapCompact records and weighted quality metrics` (weighted f1 0.75 from rows, tokCache = cache_w+cache_r), `publishes metric definitions for every managed benchmark`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "readBenchmarkSnapshot BenchmarkDefinition MetricDefinition BenchmarkTrace readEditSnapshot readSnapcompactSnapshot", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the adapter-table pattern: declared metric definitions + per-kind artifact readers returning one uniform snapshot with locator-style trace paths. This is the seam that lets one dashboard serve any future benchmark. Adapt the three kinds' parsers to your own artifact formats; omit nothing in the pattern itself. Direct tests pin both non-harbor normalizations end-to-end through the REST layer too (`manager.test.ts:250-324`).
