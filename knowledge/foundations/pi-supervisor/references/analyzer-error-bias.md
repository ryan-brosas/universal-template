<!-- capsule-v2 -->
# Analyzer error-bias contract — why must analysis failure steer when idle but continue when working?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What single function owns the fail-open/fail-closed split for supervisor outages?

## analyze (`src/core/analyzer.ts`)
**Path/Symbol:** `src/core/analyzer.ts:analyze` (:20-58).
**Signature:** `analyze(ctx, state, agentIsIdle, ineffectivePattern?, signal?, onDelta?): Promise<SteeringDecision>`.
**Data Shape:** Assembles context fresh EVERY call (extract → buildCompactionSummary → formatForSupervisor) — no memoization by design ("One-shot, no merge, no state").

### Decisive source
```ts
try {
  return await callSupervisorModel(ctx, state.provider, state.modelId,
    loadSystemPrompt(ctx.cwd).prompt, userPrompt, signal, onDelta);
} catch {
  // When idle and analysis fails, nudge rather than silently do nothing
  return agentIsIdle
    ? { action:'steer', message:'Please continue working toward the goal.',
        reasoning:'Analysis error', confidence:0 }
    : { action:'continue', reasoning:'Analysis error', confidence:0 };
}
```

**Flow:** system prompt loaded per-call (SUPERVISOR.md edits apply immediately) → compaction summary rebuilt from the full branch → user prompt assembled → judge call. The catch arm encodes the asymmetry: an idle agent with a dead supervisor would hang FOREVER on continue, so it degrades to a generic low-confidence nudge; a working agent loses nothing by waiting for the next checkpoint.
**Invariant:** (1) Failure bias is keyed to AGENT STATE, not error type — one boolean decides. (2) Degraded steers carry confidence 0, so they can never trigger the mid-run ≥0.85 gate; they only ever fire through the idle path. (3) Context is stateless-per-call, which makes the whole pipeline replayable and testable without session fixtures.
**Probe:** behavior pinned at analyzer.ts :47-57; downstream consumption of confidence gate at index.ts :216; graph pin resolves `analyze` at `src/core/analyzer.ts 20-58`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "analyze agentIsIdle Analysis error steer continue", limit: 8 });
```

## Verdict
Adopt the idle-steer/working-continue failure bias verbatim in any watchdog loop. Adapt nothing else — this capsule is host-independent.
