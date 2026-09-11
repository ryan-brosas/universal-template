<!-- capsule-v2 -->
# session-cron-task return-count protocol — why does removing scheduled tasks report how many it actually removed?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Session-only cron tasks (never persisted) and disk-backed tasks can share removal IDs — how does the caller know whether the in-memory registry already accounted for everything, without a second lookup?

## removeSessionCronTasks: count-returning batch removal
**Path/Symbol:** `src/bootstrap/state.ts`:`SessionCronTask` (`:1280-1292`), `getSessionCronTasks`/`addSessionCronTask` (`:1294-1300`), `removeSessionCronTasks` (`:1307-1315`). Related session-only flags: `scheduledTasksEnabled` gate (:134-137), teammate routing via optional `agentId` (:1286-1291).
**Signature:** `removeSessionCronTasks(ids: readonly string[]): number`; `addSessionCronTask(task: SessionCronTask): void`.
**Data Shape:** `SessionCronTask = { id, cron, prompt, createdAt, recurring?, agentId? }`. `agentId`, when set, means the task was created by an in-process TEAMMATE — the scheduler routes its fires to that teammate's pendingUserMessages queue instead of the main REPL command queue. Session-only: never written to `.claude/scheduled_tasks.json`.

### Decisive source
```ts
// :1302-1315
/**
 * Returns the number of tasks actually removed. Callers use this to skip
 * downstream work (e.g. the disk read in removeCronTasks) when all ids
 * were accounted for here.
 */
export function removeSessionCronTasks(ids: readonly string[]): number {
  if (ids.length === 0) return 0
  const idSet = new Set(ids)
  const remaining = STATE.sessionCronTasks.filter(t => !idSet.has(t.id))
  const removed = STATE.sessionCronTasks.length - remaining.length
  if (removed === 0) return 0
  STATE.sessionCronTasks = remaining        // reassign, not splice-mutate
  return removed
}
```

**Flow:** `/schedule remove <ids>` → in-memory filter first → returned count tells the caller how many IDs remain unaccounted → only if count < ids.length does the caller hit DISK (`removeCronTasks`) to clean file-backed entries sharing those ids.
**Invariant:** The boolean "did I find anything" is insufficient when two registries can claim the same ID space — the COUNT is the reconciliation signal that avoids an unconditional disk read on every removal. Empty input short-circuits BEFORE allocating the Set. Removal REASSIGNS the array (STATE.sessionCronTasks = remaining) rather than mutating in place, keeping any snapshot readers consistent. The typed task shape lives IN bootstrap (comment :140-142: importing from cronTasks.ts would break bootstrap's leaf position in the import DAG) — duplicated type, zero imports.
**Probe:** Deterministic pins: `grep -n 'number of tasks actually removed' src/bootstrap/state.ts` → `1303:`; `grep -n 'if (removed === 0) return 0' src/bootstrap/state.ts` → `1312:`; `grep -n 'keeps' src/bootstrap/state.ts | head -1` → verify; `grep -n 'bootstrap a leaf of the import DAG' src/bootstrap/state.ts` → `142:`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "removeSessionCronTasks SessionCronTask session cron", limit: 10 });
```

## Verdict
Adopt count-returning removal whenever volatile + durable stores partition one ID namespace — it converts "maybe check the disk" into arithmetic. Adapt to your persistence layout; keep the empty-input short-circuit. Omit the agentId routing field unless you have teammates.
