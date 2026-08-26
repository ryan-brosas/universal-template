<!-- capsule-v2 -->
# Baseline-vs-best naming trap — why is the field called bestMetric when it stores the baseline?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What does `state.bestMetric` actually hold at each moment, and which "best" must a porter use where?

## state.bestMetric = FIRST run's metric (baseline); findBestMetric() = true optimum
**Path/Symbol:** `harness/server.ts` — assignment :319 & :696; `findBestMetric` :214–218; snapshot disambiguation :221–234; `resetForReinit` :324–331.
**Signature:** `updateStateAfterLog(state, experiment)` sets `state.bestMetric = state.results[0]?.metric ?? null`; `findBestMetric(results, direction): number | null`.
**Data Shape:** `bestMetric: number | null` — misleadingly named; the genuine optimum over kept runs is computed on demand by `findBestMetric` (min/max by direction over `status==='keep'`).

### Decisive source
```ts
// server.ts:220-230 — the in-source comment IS the contract
function buildSessionSnapshot(state: ExperimentState): SessionSnapshot {
  // bestMetric in state is the baseline (first run). For hooks, best_metric
  // means the best kept metric across all runs.
  const bestMetric = findBestMetric(state.results, state.bestDirection);
  return { metric_name: ..., baseline_metric: state.bestMetric, best_metric: bestMetric, ... };
}
```

**Flow:** every log (`updateStateAfterLog` :317–322) and every JSONL reconstruction (:695–701) re-pins `bestMetric` to the CURRENT SEGMENT's first result's metric. Re-init nulls it until a new baseline logs (`resetForReinit`). Consumers that want the real best call `findBestMetric`: hook snapshots (:224), status action (:1493–1500 loops keeps with `isBetter`), UI widgets (index.ts :222–235, widget.ts :93–107, table.ts :39–52 all reverse-loop keeps). Delta displays divide by this BASELINE (`log` text :1305–1310, dashboard pct lines).
**Invariant:** never "fix" `bestMetric` to track the optimum — confidence math depends on baseline identity (`computeConfidence` uses `validResults[0]`, and its `bestKept === baseline ⇒ null` gate assumes the distinction), and every "(+x.x%)" delta in UI/CLI output is measured against the FIRST run of the segment, not the running best. The hook payload renames the pair explicitly (`baseline_metric` vs `best_metric`) because the wire format cannot afford the ambiguity.
**Probe:** anchors from repo root: `grep -c 'state.bestMetric = state.results\[0\]?.metric ?? null' harness/server.ts` → 1 (:319 inside updateStateAfterLog); the reconstruction twin uses the longer receiver form — `grep -n 'session.state.bestMetric = session.state.results\[0\]' harness/server.ts` → exactly :696; `grep -n 'findBestMetric' harness/server.ts` → :214 (def) + :224 (snapshot call only).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "buildSessionSnapshot baseline_metric best_metric findBestMetric", limit: 10 });
```

## Verdict
Adopt the two-name discipline verbatim (baseline persisted in state; best derived on demand) and keep the in-source comment; adapt naming if porting to a language with richer types (e.g. rename to `baselineMetric` everywhere EXCEPT the JSONL/hook wire keys); omit nothing — misporting this silently corrupts every percentage shown to the user.
