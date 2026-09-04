<!-- capsule-v2 -->
# Best-of-N run selection — ghost runs, transport failures, and the strict best-run ordering

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** When each benchmark task is attempted N times, which run represents the task — and how do you classify the failed attempts so stalls don't poison the score denominator?

## success > non-ghost > cheaper > earlier ordering; ghost/transport exclusion
**Path/Symbol:** `packages/metaharness/adapters/edit/runner.ts`:`isGhostRun` (1806-1811), `isTransportFailure` (1798-1804), `isBetterRun` (1831-1838), `pickBestRunIndex`/`summarizeTaskRuns` (1840-1879), `percentile` (1932-1942).
**Signature:** `isGhostRun(r: TaskRunResult): boolean`; `pickBestRunIndex(orderedRuns: TaskRunResult[]): number` (-1 when empty); `percentile(sortedAscending: readonly number[], p: number): number`.
**Data Shape:** `TaskRunResult = { runIndex, success, tokens{input,output,reasoning,total}, toolCalls{read,edit,write,...}, error?, duration, retryStats? }`. Task summary reports best-run stats plus `flakeSuccessRate` over non-ghost runs.

### Decisive source
```ts
function isTransportFailure(r: TaskRunResult): boolean {
    if (r.success) return false;
    // Provider/transport stalls retried until the cap was hit. These don't
    // reflect edit-tool quality, so we exclude them from the score denominator.
    return err.includes("Timeout exhausted");
}
function isGhostRun(r: TaskRunResult): boolean {
    if (r.success) return false;
    const noProgress = r.tokens.total === 0 && r.toolCalls.read === 0 &&
                       r.toolCalls.edit === 0 && r.toolCalls.write === 0;
    return noProgress || isTransportFailure(r);
}
// Strict ordering used to pick the "best" run for a task:
//   1. Successful runs win over failed runs.
//   2. Then prefer non-ghost runs (real work over 0/0/0 stalls).
//   3. Then prefer the run with lower total token usage.
//   4. Then prefer the earlier runIndex for stability.
function isBetterRun(a: TaskRunResult, b: TaskRunResult): boolean {
    if (a.success !== b.success) return a.success;
    if (aGhost !== bGhost) return !aGhost;
    if (a.tokens.total !== b.tokens.total) return a.tokens.total < b.tokens.total;
    return a.runIndex < b.runIndex;
}
```

**Flow:** all N ordered runs of a task are scanned by `pickBestRunIndex` under the four-level comparator → `summarizeTaskRuns` reports the best run's tokens/duration/toolCalls as THE task's stats, computes `editSuccessRate` (defaulting to 1 when no edits were attempted), `autocorrectFreeSuccess`, and `flakeSuccessRate` = successful/nonGhost (flakiness indicator: task passed overall but some real runs failed) → summary-level: primary metrics aggregate BEST runs only; diagnostic counts (ghostRuns, transportFailures, retries) span every executed run; token distributions report median/p1/p99 via linear-interpolated type-7 percentile. A task with zero completed runs still appears (`bestRunIndex: -1`) so snapshots work mid-run.
**Invariant:** a successful run can never be a ghost; ghost/stalled failures are EXCLUDED from denominators (score measures capability, not provider weather); ties break toward determinism (lower cost, then earlier index); "no edit attempts" must not count as a 0% edit-success rate.
**Probe:** `packages/metaharness/adapters/edit/runner.test.ts:63-358` — `picks the successful run with the lowest tokens as the task best` (success beats cheaper failure; flakyTasks=1), `falls back to the cheapest failure when no run succeeded`, `ignores ghost runs when picking the best non-successful run` (summary.ghostRuns=1), `reports median, p1, and p99 token stats across best runs` (exact interpolation values).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "isGhostRun isTransportFailure isBetterRun pickBestRunIndex summarizeTaskRuns percentile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the classification + comparator verbatim for any N-attempts-per-task evaluation: it cleanly separates "the model couldn't do it" from "the provider stalled" and keeps headline numbers on best-run while keeping diagnostics honest. Adapt the progress signature (here tokens+tool calls) and the stall marker string to your domain; omit the hashline-specific fields. Five direct tests pin ordering, ghosts, and percentiles with exact numeric expectations.
