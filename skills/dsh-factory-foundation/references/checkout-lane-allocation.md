<!-- capsule-v2 -->
# Checkout lanes — how does each task pick its workspace, and when is a worktree cleaned up or swept?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I allocate git workspaces per task (shared / isolated / reused) and garbage-collect them safely?

## allocateCheckout / cleanupCheckout / sweep
**Path/Symbol:** `packages/scheduler/src/index.ts` (`allocateCheckout`, `cleanupCheckout`, `sweep`) (:323–347, :405–433).
**Signature:** `private async allocateCheckout(claim): Promise<string>`; cleanup only under `cleanupPolicy === 'remove-succeeded'`; sweep every `sweepOlderThanMs` (default 7d) with `sweepLimit=8`.
**Data Shape:** lane modes `current | isolated | reuse(+reuseTaskId)`; baseRef precedence task.lane.baseRef → project.defaultRef → `'head'`.

### Decisive source
```ts
if (claim.task.lane.mode === 'current') return claim.project.mainPath
if (claim.task.lane.mode === 'reuse') {
    const source = stored.document.tasks.find(task => task.id === claim.task.lane.reuseTaskId)
    if (source?.output?.checkoutPath === undefined) throw new Error(`${claim.task.identifier} reuse source has no checkout output`)
    return source.output.checkoutPath
}
...
const baseRef = claim.task.lane.baseRef !== undefined ? { ref: claim.task.lane.baseRef }
    : claim.project.defaultRef !== undefined ? { ref: claim.project.defaultRef } : 'head' as const
// cleanup:
const stillNeeded = stored.document.tasks.some(task => task.lane.reuseTaskId === claim.task.id
    && !['succeeded', 'failed', 'cancelled'].includes(task.status))
if (stillNeeded) return
```

**Flow:** current → main checkout path; reuse → predecessor's persisted output.checkoutPath (missing = hard error); recurring tasks RE-FIND their previous worktree before creating a new one; otherwise create a labeled worktree at the resolved baseRef. After success under `remove-succeeded`: delete the worktree ONLY if no non-terminal reuser still points at it; failures preserve it for debugging. The weekly sweep skips whole PROJECTS that still have an active reuser.
**Invariant:** Reuse chains read the PREDECESSOR's durable output, never live scheduler memory — so a reused checkout survives restarts; deletion is reference-checked against downstream tasks (still-needed guard) and best-effort (remove failure logs and preserves); recurring continuity means a scheduled task keeps ONE persistent workspace across runs.
**Probe:** `packages/domain/tests/domain.spec.ts` "serializes current-checkout tasks even when global capacity remains" (lane exclusivity) + scheduler harness pins setup runs in the CURRENT lane (`workdir: projectPath`). Deterministic from repo root: `grep -c 'reuse source has no checkout output' packages/scheduler/src/index.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "allocateCheckout", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt the three-lane allocation + reference-checked deletion + project-level sweep skip. Adapt to host worktree tooling. Omit provider registration details.
