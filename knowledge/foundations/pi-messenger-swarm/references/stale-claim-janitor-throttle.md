<!-- capsule-v2 -->
# Throttled stale-claim janitor — how do crashed agents release their tasks without any watchdog process?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** Who releases a task whose claiming agent died mid-run?

## Cleanup piggybacked on reads, throttled 5s per session
**Path/Symbol:** `swarm/task-store/cleanup.ts:cleanupStaleTaskClaims` (:29-86), `swarm/task-store/queries.ts:getTasks` (:105-121) + `CLEANUP_THROTTLE_MS = 5_000` (:11), private twin `queries.ts:isAgentActive` (:26-37).
**Signature:** `cleanupStaleTaskClaims(cwd, sessionId): number`; `getTasks(cwd, sessionId): SwarmTask[]`.
**Data Shape:** three-state liveness: registry file + alive pid ⇒ active(`true`); registry file + dead pid ⇒ crashed(`false`); NO registry file ⇒ departed(`null`) — released ONLY if some other agents are still known.

### Decisive source
```ts
// Use replayTasks directly instead of getTasks to avoid triggering cleanup recursively
const tasks = replayTasks(cwd, sessionId);
...
} else if (active === null && knownAgents.length > 0) {
  appendTaskEvent(... 'released' ...);
  logFeedEvent(cwd, task.claimed_by, 'task.reset', task.id,
    'agent left - task auto-unclaimed', task.channel ?? 'unknown');
```

**Flow:** every `getTasks` call first checks a `${cwd}:${sessionId}` throttle timestamp; when >5s since last sweep it runs the janitor BEFORE replaying: each `in_progress` task's claimant is probed against `<cwd>/.pi/messenger/registry/<name>.json` pid liveness; crashed or (departed ∧ others-known) claimants get a synthetic `released` event appended plus a `task.reset` feed line.
**Invariant:** The janitor must call `replayTasks`, NOT `getTasks`, or it recurses infinitely through its own trigger. Departed-claimant tasks are preserved while the mesh is empty (registry wiped) so a lone offline agent doesn't lose work to a spurious cleanup. `_resetCleanupThrottle` exists purely as a test seam.
**Probe:** direct tests `tests/swarm/task-cleanup-throttle.test.ts::should auto-unclaim tasks from crashed agents when getTasks is called` (dead pid 99999 vs live `process.pid`) and `::should throttle cleanup calls to avoid excessive checks`; `grep -c "avoid triggering cleanup recursively" swarm/task-store/cleanup.ts swarm/task-store/queries.ts` (=1 each).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "cleanupStaleTaskClaims CLEANUP_THROTTLE_MS isAgentActive auto-unclaimed", limit: 5 });
```

## Verdict
Adopt read-triggered, throttled, PID-liveness janitorship as the no-watchdog crash recovery pattern; adapt thresholds; omit the knownAgents-empty guard only if your registry can never be transiently unreadable.
