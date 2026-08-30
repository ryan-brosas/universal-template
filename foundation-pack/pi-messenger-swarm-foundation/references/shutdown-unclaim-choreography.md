<!-- capsule-v2 -->
# Shutdown unclaim choreography — what must happen when an agent (or its parent) leaves the mesh mid-work?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** Which claims are released at shutdown, by whom, and in what order?

## Own claims first, then every claim held by my spawned agents
**Path/Symbol:** `extension/shutdown.ts:handleSessionShutdown` (:15-71); caller `index.ts:session_shutdown` (:415-432).
**Signature:** `handleSessionShutdown(state, dirs): Promise<ShutdownResult>` returning `{unclaimedCount}`.
**Data Shape:** two filters over replayed tasks: `claimed_by === state.agentName`, then `spawnedNames.has(claimed_by)` where spawnedNames = ALL history names of this session.

### Decisive source
```ts
const spawnedAgents = listSpawnedHistory(cwd, sessionId);
const spawnedNames = new Set(spawnedAgents.map((s) => s.name));
...
// Unclaim tasks claimed by spawned agents
const spawnedClaimedTasks = allTasks.filter(
  (t) => t.status === 'in_progress' && t.claimed_by && spawnedNames.has(t.claimed_by)
);
for (const task of spawnedClaimedTasks) {
  taskStore.unclaimTask(...);
  logFeedEvent(cwd, task.claimed_by!, 'task.reset', task.id,
    'parent agent left - task unclaimed', ...);
```

**Flow:** leave feed event ordering: own unclaims (reason `'agent left - task unclaimed'`) → spawned-agent unclaims (`'parent agent left - task unclaimed'`) → single `leave` event → registry unlink via `store.unregister`. The harness daemon is deliberately NOT quit by the extension — only the process IT spawned is stopped; the shared daemon survives for other sessions.
**Invariant:** Parent-death cascades ownership release because orphaned spawned agents have no session_shutdown of their own — the parent is their janitor. Unclaim (not reset) is used deliberately: attempt_count and progress_log survive, status returns to todo. Porters who only unregister (skip unclaims) strand in_progress tasks until the read-path janitor notices dead pids — which never fires while the parent's pid is still alive.
**Probe:** direct tests `tests/swarm/session-shutdown-cleanup.test.ts::should unclaim tasks claimed by spawned agents` (:113), `::should only unclaim tasks for the specific agent, not others` (:248), `::should clean up file reservations when agent leaves` (:375); `grep -c "parent agent left - task unclaimed" extension/shutdown.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "handleSessionShutdown unclaimTask listSpawnedHistory unregister", limit: 5 });
```

## Verdict
Adopt parent-as-janitor shutdown semantics with reason-differentiated feed events and unclaim-not-reset; adapt event wording; omit reservation cleanup notes if you have no file-reservation concept.
