<!-- capsule-v2 -->
# Spawned-agent event-sourced lifecycle — how does a subagent's state survive harness restarts and outlive its parent process?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How is a spawned child process tracked from spawn to terminal event, including across server death?

## JSONL spawn log + in-memory runtimes + detached restore
**Path/Symbol:** `swarm/spawn.ts:spawnSubagent` (:450-557), `appendEvent` (:68-72), `loadSpawnedAgents` (:77-101), `runtimes` map (:29), `restoreRuntimeEntries` (:941-992), `startDetachedPolling` (:1020-1087).
**Signature:** `spawnSubagent(cwd, request: SpawnRequest, sessionId, inheritedChannel?): SpawnedAgent`; events `{ id, type: 'spawned'|'completed'|'failed'|'stopped'|'progress', timestamp, agent: Partial<SpawnedAgent> }`.
**Data Shape:** `<cwd>/.pi/messenger/agents/<safeSessionId>.jsonl` (event log) + sibling dir `<safeSessionId>/<name>-<id>.md` (regenerated human-readable agent file with YAML frontmatter).

### Decisive source
```ts
const merged: SpawnedAgent = existing
  ? { ...existing, ...event.agent, id: event.id }   // PARTIAL merge: later events patch fields
  : { ...(event.agent as SpawnedAgent), id: event.id };
```
```ts
// detached restore: no ChildProcess handle — a fake process delegating kill() to the PID
const fakeProcess = { pid: entry.pid, exitCode: null as number | null,
  kill: (sig?: string) => { try { process.kill(entry.pid, sig as any); } catch {} return true; },
  on: () => fakeProcess as any, stdout: null as any, ...
} as unknown as ChildProcess;
```

**Flow:** spawn appends `spawned` (full record incl. systemPrompt) → after the real pid exists appends `progress` carrying just `{pid}` → close handler classifies signal/stopping/code into completed|failed|stopped and appends the terminal partial → every read folds the log by merge-spread so the last event wins per field. If the SERVER dies first, startup runs two recovery paths: `restoreRuntimes` replays `spawn-runtimes.json` (persisted on graceful quit) and `reconcileAndRestoreOrphans` rescans ALL session jsonl logs for status-running agents with live pids; both create detached runtimes polled every 5s.
**Invariant:** Terminal-event dedup is load-bearing: before the detached poller writes its own `failed`, it re-reads the jsonl and ADOPTS any existing terminal event (`alreadyFinalized`) so a legitimate `completed` from the dying server's close handler can't be overwritten. Merge semantics are field-level spread, never replace-whole — porters who replace lose earlier fields like name/taskId.
**Probe:** direct tests `tests/swarm/spawn-event-sourcing.test.ts::merges multiple events for same agent` (:195) and `::last event wins for same agent` (:334), `tests/swarm/reconcile-spawned-agents.test.ts::marks a running agent as failed when its PID is dead` (:101), `tests/swarm/cleanup-exited-spawned.test.ts::persists agents killed by SIGTERM as stopped` (:136); `grep -c "alreadyFinalized" swarm/spawn.ts` (=3).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "spawnSubagent loadSpawnedAgents restoreRuntimes reconcileAndRestoreOrphans startDetachedPolling", limit: 8 });
```

## Verdict
Adopt partial-merge event sourcing for process lifecycles plus the dual restore path (persisted-runtimes file + orphan rescan) and adopt-don't-duplicate terminal events; adapt the pi-specific spawn args; omit the markdown agent-file rendering if unused.
