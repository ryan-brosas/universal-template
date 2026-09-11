<!-- capsule-v2 -->
# cost-state restore with wall-clock rebase — how does a resumed session show cumulative duration without counting downtime?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Session totals (cost, API time, lines changed, per-model usage) live in process memory — how does `--resume` restore them AND make total wall duration continue from where the old session left off?

## setCostStateForRestore: field transplant + startTime rebasing
**Path/Symbol:** `src/bootstrap/state.ts`:`setCostStateForRestore` (`:881-916`), reset twin `resetCostState` (`:864-875`), test-only nuke `resetStateForTests` (`:919-930`), totals accessors (`:566-621`, `:704-722` sumBy over modelUsage).
**Signature:** `setCostStateForRestore({ totalCostUSD, totalAPIDuration, totalAPIDurationWithoutRetries, totalToolDuration, totalLinesAdded, totalLinesRemoved, lastDuration?, modelUsage? }): void` (called by cost-tracker.ts `restoreCostStateForSession`).
**Data Shape:** Cumulative scalars + `modelUsage: { [modelName]: ModelUsage }` + optional `lastDuration` (the PREVIOUS session's wall duration). Token/cost aggregates derive at read time via lodash `sumBy` over modelUsage values (:704-722) — never stored separately.

### Decisive source
```ts
// :906-916
  // Restore per-model usage breakdown
  if (modelUsage) {
    STATE.modelUsage = modelUsage
  }
  // Adjust startTime to make wall duration accumulate
  if (lastDuration) {
    STATE.startTime = Date.now() - lastDuration
  }
```

**Flow:** resume loads prior session's summary → transplants every cumulative scalar + per-model usage map → rebases `startTime = now − previousDuration` so `getTotalDuration()` (which computes `Date.now() − STATE.startTime`, :574-576) reports OLD+NEW wall time → session continues accruing on top.
**Invariant:** Duration is DERIVED (`now − startTime`) but must ACCUMULATE across resumes — the only way to satisfy both is to move the anchor backwards by exactly the restored duration. Downtime between sessions is intentionally INCLUDED (wall-clock semantics), while API/tool durations are transplanted as-is because they were measured, not derived. Derived aggregates stay derived: input/output/cache tokens are never persisted as separate totals; they're recomputed from the per-model map so restore can't introduce drift between breakdown and total. `resetStateForTests` restores from `getInitialState()` wholesale and additionally clears module-level turn-budget slots (:926-929) — the singleton has state BOTH in STATE and in module lets.
**Probe:** Deterministic pins: `grep -n 'Adjust startTime to make wall duration accumulate' src/bootstrap/state.ts` → `912:`; `grep -n 'Date.now() - lastDuration' src/bootstrap/state.ts` → `914:`; `grep -n "sumBy(Object.values(STATE.modelUsage)" src/bootstrap/state.ts | wc -l` → `5`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "setCostStateForRestore restoreCostStateForSession cost restore", limit: 10 });
```

## Verdict
Adopt anchor-rebasing for any derived "time since X" metric that must survive process restarts, and keep derived aggregates computed-at-read. Adapt the summary schema to your transcript format. Omit the ant/test-only resets when porting outside a test-heavy monorepo.
