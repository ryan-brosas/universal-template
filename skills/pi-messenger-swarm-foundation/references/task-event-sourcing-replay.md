<!-- capsule-v2 -->
# Task event-sourcing replay machine — why is every task mutation an appended event instead of a rewritten state file?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How do concurrent agents mutate shared task state without corrupting it?

## Append event → replay-to-map on every read
**Path/Symbol:** `swarm/task-store/events.ts:appendTaskEvent` (:18-22), `swarm/task-store/events.ts:replayEventsToMap` (:27-158), `swarm/task-store/events.ts:replayTasks` (:170-175).
**Signature:** `appendTaskEvent(cwd, sessionId, event: TaskEvent): void`; `replayEventsToMap(cwd, sessionId): Map<string, SwarmTask>`.
**Data Shape:** `<cwd>/.pi/messenger/tasks/<safeSessionId>.jsonl`, one `TaskEvent { taskId, type: 'created'|'claimed'|'released'|'progress'|'completed'|'blocked'|'unblocked'|'reset'|'archived', timestamp, agent?, channel?, payload? }` per line. Nine event types; unknown types are silently ignored (forward compat).

### Decisive source
```ts
case 'claimed': {
  if (!existing) continue;                     // claim before create is dropped
  existing.status = 'in_progress';
  existing.claimed_by = event.agent;
  ...
  existing.attempt_count = (existing.attempt_count ?? 0) + 1;
  break;
}
case 'unblocked': {
  if (existing.claimed_by) existing.status = 'in_progress';
  else existing.status = 'todo';               // unblock restores PRE-block status from live fields
  delete existing.blocked_reason; delete existing.blocked_by;
```

**Flow:** every command (create/claim/unclaim/block/unblock/complete/reset/archive/delete) appends exactly one event then returns the REPLAYED task — there is no mutable state file at all; each read folds the whole log deterministically. `released` deletes claim fields; `reset` wipes claim AND completion AND block fields; `archived` flips status but `replayTasks` filters archived out while `replayAllTasks` keeps them.
**Invariant:** Event handlers must tolerate out-of-order/duplicate delivery because they guard `if (!existing) continue` — claims arriving before creates are no-ops, not crashes. Attempt counting lives in replay (claimed increments), NOT in the writer, so replays are idempotent per log content. Sorting after fold is by trailing numeric id with MAX_SAFE_INTEGER fallback.
**Probe:** direct tests `tests/swarm/task-event-sourcing.test.ts::replays claim event to in_progress status` (pins attempt_count=1), `::replays unclaim back to todo`, `::skips malformed lines`-class behavior via `tests/swarm/spawn-event-sourcing.test.ts::last event wins for same agent`; `grep -c "if (!existing) continue" swarm/task-store/events.ts` (=8 — one per event arm that requires prior state).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "replayEventsToMap appendTaskEvent replayTasks claimed released reset archived", limit: 8 });
```

## Verdict
Adopt append-only event log + deterministic fold for any shared agent work queue; adapt the nine-type vocabulary to your domain; omit the spec-file sidecar (`persistence.ts`) if tasks carry all content inline.
