<!-- capsule-v2 -->
# Stalled task detection — how does the coordinator find workers that went quiet?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What clock defines "stalled" and which tasks are exempt?

## Last-activity = last progress entry, else claimed_at
**Path/Symbol:** `swarm/task-store/queries.ts:getStalledTasks` (:158-178); presenter `swarm/handlers/task-query.ts:taskStalled` (:86-117).
**Signature:** `getStalledTasks(cwd, sessionId, stallThresholdMs = 10 * 60 * 1000): SwarmTask[]`.
**Data Shape:** filter over in_progress tasks only; activity timestamp from `progress_log[last].timestamp` when any progress exists, else `claimed_at`.

### Decisive source
```ts
return tasks.filter((task) => {
  if (task.status !== 'in_progress') return false;
  const lastActivity = task.progress_log?.length
    ? task.progress_log[task.progress_log.length - 1].timestamp
    : task.claimed_at;
  if (!lastActivity) return false;               // no clock ⇒ never stalled
  return now - Date.parse(lastActivity) >= stallThresholdMs;
});
```

**Flow:** every progress event appends to progress_log during replay, so ANY `task.progress` call refreshes the clock; blocked/done/todo are exempt by the status gate regardless of age. The handler renders each stalled task with minutes-since-activity plus two remediation hints (ping the agent / reset the task).
**Invariant:** The dual-clock fallback means a claimant that NEVER posts progress is judged solely by claimed_at — but a missing BOTH (`!lastActivity`) is treated as not-stalled rather than stalled (conservative default). Threshold 10min is the default knob, overridden per-call in tests with 0.
**Probe:** direct tests `tests/swarm/task-stalled.test.ts::returns task when claim is older than threshold` (:86), `::uses progress_log last entry as activity timestamp when present` (:100), `::ignores done tasks regardless of age` (:131), `::ignores blocked tasks...` (:139); `grep -c "10 * 60 * 1000" swarm/task-store/queries.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "getStalledTasks progress_log claimed_at stallThresholdMs", limit: 5 });
```

## Verdict
Adopt progress-log-preferred/claim-fallback clocking with conservative no-clock exemption; adapt threshold; wire into your own coordinator loop — this repo only exposes it via CLI.
