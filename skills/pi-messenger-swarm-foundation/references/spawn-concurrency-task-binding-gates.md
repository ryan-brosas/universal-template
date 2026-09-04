<!-- capsule-v2 -->
# Spawn concurrency gate + task-binding guardrail — what stops a coordinator from flooding providers or stealing its own work?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What guards run BEFORE a subagent process is created?

## Ready-task nag + running-count ceiling
**Path/Symbol:** `swarm/handlers/spawn.ts:spawnCreate` (:171-302), default limit 3 (:204), `swarm/spawn.ts:getRunningSpawnCount` (:772-785).
**Signature:** `executeSpawn(op, params, state, cwd, sessionId, maxConcurrentSpawns?)`; guard fires only when `op == null` (create path).
**Data Shape:** refusal details carry `error: 'missing_task_id' | 'concurrency_limit'` plus readyTasks/running/limit payloads.

### Decisive source
```ts
// Guardrail: if the user has ready tasks but forgot --task-id, warn them
if (!params.taskId && !params.force) {
  const ready = taskStore.getReadyTasks(cwd, sessionId);
  if (ready.length > 0) { return result(`⚠️  You have ${ready.length} ready task${...}...`, {...}); }
}
const running = getRunningSpawnCount(cwd);
const limit = maxConcurrentSpawns ?? 3;
if (running >= limit) {
  return result(`Error: ${running} subagents already running (limit: ${limit}). ...`,
    { mode: 'spawn', error: 'concurrency_limit', running, limit });
}
```

**Flow:** every create first runs `cleanupExitedSpawned` + `reconcileSpawnedAgents` (self-heal before counting), then the two gates: (1) unbound spawn with ready tasks ⇒ refuse with an actionable list unless `--force`; (2) live spawn count ≥ limit ⇒ refuse naming the config knob `.pi/pi-messenger.json:maxConcurrentSpawns`. List/history/stop ops bypass both gates.
**Invariant:** The count is per-cwd (`getRunningSpawnCount(cwd)` filters runtimes by record.cwd) so multi-project servers sharing one harness don't starve each other; detached (restored) runtimes count only if their PID is alive. The task-binding gate exists because the swarm protocol tells spawned agents to claim their bound task — an unbound parent spawn tends to claim work meant for children.
**Probe:** direct tests `tests/swarm/spawn-concurrency.test.ts::rejects spawn when at the concurrency limit`, `::uses default limit of 3 when maxConcurrentSpawns is not provided`, `::non-create spawn operations bypass concurrency check`, and `tests/swarm/router.test.ts::rejects spawn without objective text`; `grep -n "maxConcurrentSpawns ?? 3" swarm/handlers/spawn.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "spawnCreate maxConcurrentSpawns getRunningSpawnCount missing_task_id force", limit: 6 });
```

## Verdict
Adopt pre-spawn self-heal + ready-task binding nag + per-project concurrency ceiling as one composite gate; adapt defaults (3) and the force escape hatch policy; omit the ready-task nag if your agents never delegate via task binding.
