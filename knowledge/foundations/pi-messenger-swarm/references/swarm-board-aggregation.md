<!-- capsule-v2 -->
# Swarm board & summary aggregation — how does the `swarm` action compose tasks + agents + cleanup into one view?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What is the read pipeline behind the swarm board and its summary line?

## Self-heal → replay → bucket counts → bounded rendering
**Path/Symbol:** `swarm/handlers/status.ts:executeSwarmStatus` (:8-84), `_utils.ts:summaryLine`, store-side `queries.ts:getSummaryForTasks` (:139-147) / `getReadyTasksForTasks` (:153-156).
**Signature:** `executeSwarmStatus(cwd, channelId, sessionId)`.
**Data Shape:** `SwarmSummary { total, todo, in_progress, done, blocked }` (archived excluded by upstream filter); running agents capped at 8 display rows.

### Decisive source
```ts
export function executeSwarmStatus(cwd: string, channelId: string, sessionId: string) {
  cleanupExitedSpawned(cwd, sessionId);      // finalize dead children BEFORE counting
  reconcileSpawnedAgents(cwd, sessionId);    // tombstone crashed ones from prior servers
  const tasks = taskStore.getTasks(cwd, sessionId);   // ALSO triggers stale-claim janitor
```
Empty-state variant still reports history:
```ts
if (tasks.length === 0 && runningAgents.length === 0) {
  ... `${completedCount} completed, ${failedCount} failed agents in history.`
```

**Flow:** every board render first finalizes zombie spawn records and runs the throttled claim janitor (via getTasks), then replays tasks for status buckets and folds spawned history into running/completed/failed counts; output renders Running Agents (≤8), Agent History line, and full task list with status icons/owner/dep arrows.
**Invariant:** Read paths are self-healing — a porter who skips cleanupExitedSpawned/reconcile before counting will report ghosts as "running". The empty-state branch preserves history counts so a finished swarm doesn't look wiped.
**Probe:** direct tests `tests/swarm/router.test.ts::returns swarm board summary` (:174), `tests/swarm/cleanup-exited-spawned.test.ts::returns 0 for cleanup when agents already persisted by close handler` (:201), `tests/swarm/litmus-statusbar.test.ts::shows empty-state status when no tasks exist` (:33); `grep -c "cleanupExitedSpawned" swarm/handlers/status.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "executeSwarmStatus summaryLine getSummaryForTasks getReadyTasksForTasks", limit: 5 });
```

## Verdict
Adopt heal-before-read aggregation and the five-bucket summary; adapt icons/row caps; keep the empty-state history line for post-mortem UX.
