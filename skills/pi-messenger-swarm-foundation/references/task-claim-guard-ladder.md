<!-- capsule-v2 -->
# Task claim guard ladder — which checks gate a claim and what error taxonomy distinguishes them?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How does `task.claim` decide between success, already-claimed, done, and dependency-blocked?

## Store-level single gate + handler-level re-derivation
**Path/Symbol:** `swarm/task-store/commands.ts:claimTask` (:58-85), `swarm/handlers/task-lifecycle.ts:taskClaim` (:11-80).
**Signature:** `claimTask(cwd, sessionId, taskId, agentName, reason?): SwarmTask | null` — null means "refused", reason recovered by the caller.
**Data Shape:** refusal taxonomy in handler: `not_found | already_claimed | already_done | not_ready` (dependency unmet); store returns bare null for all of them.

### Decisive source
```ts
// claimTask (store): the ONLY mutation gates
if (!task) return null;
if (task.status !== 'todo') return null;
const doneIds = new Set(allTasks.filter((t) => t.status === 'done').map((t) => t.id));
const unmetDeps = task.depends_on.filter((dep) => !doneIds.has(dep));
if (unmetDeps.length > 0) return null;
appendTaskEvent(... 'claimed' ...);
```
```ts
// taskClaim (handler): re-reads to name WHY it refused
const existing = taskStore.getTask(cwd, sessionId, params.id);
if (existing.status === 'in_progress') → already_claimed (+ claimedBy)
if (existing.status === 'done')          → already_done
return ... 'not ready to claim (check dependencies)'  // residual = not_ready
```

**Flow:** handler calls store; on null, re-fetches the task and walks a status ladder to produce a distinct error code + human text. Note the ordering trap: `in_progress` is checked before `done`, so an agent seeing its OWN claim gets `already_claimed` naming itself. A parallel pure helper (`swarm/task-actions.ts:executeTaskAction` :42-71) additionally treats "already claimed BY ME" as idempotent success.
**Invariant:** Claim legality is evaluated against the REPLAYED state at event-append time — there is no reservation window; two agents racing both pass the status check only if the log shows todo for both, and last append wins with attempt_count incremented per replay. Dependencies are checked against CURRENT done set at claim time, never at create time.
**Probe:** direct tests `tests/swarm/router.test.ts::supports task create/claim/done end-to-end` and `tests/swarm/task-actions.test.ts::start blocks on unmet dependencies`; `grep -c "already_claimed" swarm/handlers/task-lifecycle.ts` (=1); `grep -n "status !== 'todo'" swarm/task-store/commands.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "claimTask taskClaim unmetDeps already_claimed not_ready", limit: 5 });
```

## Verdict
Adopt the null-store + handler-rederivation split (keeps the store pure and the UX precise) and the four-way refusal taxonomy; adapt wording/emojis; omit the coordinator self-claim warning unless you have spawned-agent delegation semantics.
