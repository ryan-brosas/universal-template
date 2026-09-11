<!-- capsule-v2 -->
# Orchestration: serial-per-platform, parallel-across-platforms — how do you run many browser workflows without ever double-driving one profile?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Given workflows bound to different platform profiles, what concurrency shape lets them overlap safely, and how are per-run results aggregated for a caller?

## Group-by-platform queues with lock-guarded execution
**Path/Symbol:** `scripts/workflow-engine.ts`:`orchestrate` command, `executeWorkflow` (`:269-316`, `:741-800`).
**Signature:** CLI: `orchestrate --ids <id1,id2,...>`; `executeWorkflow(def): Promise<{ id, platform, run|null, skipped? }>`; process exits 1 if ANY result failed.
**Data Shape:** `groups: Map<platform, WorkflowDefinition[]>` (no-platform defs group under `_none`); aggregated summary `{ requested, missing, results: [{ id, platform, status, stepsCompleted, stepsTotal, skipped? }] }` printed as ONE stdout JSON line.

### Decisive source
```ts
// One serial queue per platform; run all queues in parallel.
await Promise.all(
  [...groups.entries()].map(async ([platform, list]) => {
    for (const def of list) {
      // Stop signal: a `stop --id <thisId>` flips status to 'stopped'.
      const st = loadState().workflows[def.id]
      if (st?.status === 'stopped') {
        results.push({ id: def.id, platform: def.platform ?? null, run: null, skipped: 'stopped' })
        continue
      }
      results.push(await executeWorkflow(def))
    }
  }),
)
```
with lock-guarded execution inside `executeWorkflow`:
```ts
if (platform && !acquireLock(platform, def.id)) {
  return { id: def.id, platform, run: null, skipped: 'platform busy' }
}
try { /* mark running under state mutex → spawn → finalize under fresh read */ }
finally { if (platform) releaseLock(platform, def.id) }
```

**Flow:** parse ids (unknown ids reported on stderr, not fatal — they land in `missing`) → group by platform → run one async queue PER platform concurrently; within a queue strictly sequential because a profile has ONE active tab → each run re-checks the stop signal before starting, skips as 'busy' if the lock is held, and finalizes via a fresh state read inside the in-process mutex → aggregate everything into a single JSON summary line; non-zero exit iff any run failed.
**Invariant:** Concurrency across platforms is unbounded Promise.all, but concurrency WITHIN a platform is exactly 1 — enforced twice (queue order AND the platform lock, which also covers daemons/start children from other processes). Every skipped reason ('stopped', 'platform busy', executor-missing) is surfaced in the summary instead of being swallowed.
**Probe:** No direct test for orchestrate (coverage caveat — source-grounded). Deterministic probe: `search_graph --name-pattern "^executeWorkflow$"` resolves `locoagent.scripts.workflow-engine.executeWorkflow` (:269-316); the state mutex it uses is documented at `workflow-engine.ts:249-262`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "orchestrate executeWorkflow platform serial parallel", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt group-by-resource queues with serial-within/parallel-across execution, pre-run stop re-check, skip-reason reporting, single-line JSON aggregation, and any-failure exit code. Adapt the resource key (platform here; could be account/workspace). Omit nothing about the double enforcement — dropping either the queue or the lock re-opens the same-profile race.
