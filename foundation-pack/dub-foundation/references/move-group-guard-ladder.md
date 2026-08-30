<!-- capsule-v2 -->
# Move-group execution — how do you make an auto-assignment workflow safe to re-fire and impossible to loop?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** Which guards must a "move partner to another group when metrics match" workflow carry so retries, duplicate events, and manual overrides can't cause thrash?

## executeMoveGroupWorkflow: fresh-read → skip gates → NX lock → move in finally-cleared lock
**Path/Symbol:** `apps/web/lib/api/workflows/move-group/execute.ts:executeMoveGroupWorkflow` (:11-133).
**Signature:** `executeMoveGroupWorkflow({ workflow: Workflow, context: WorkflowContext }): Promise<void>` — every exit path is a logged `return` (never throws past the orchestrator's catch).
**Data Shape:** action payload `{ groupId: newGroupId }`; context supplies identity + `metrics.aggregated`; evaluation context is built HERE from aggregated metrics + the FRESH groupId.

### Decisive source
```ts
// Fetch program enrollment to get fresh groupId
const programEnrollment = await prisma.programEnrollment.findUniqueOrThrow({
  where: { partnerId_programId: { partnerId, programId } },
  select: { groupId: true, groupMoveDisabledAt: true },
});
if (programEnrollment.groupId === newGroupId) return;      // already there
if (programEnrollment.groupMoveDisabledAt) return;         // manual override wins
// ...
const lockKey = `workflow:moveGroup:${programId}:${newGroupId}:${partnerId}`;
const acquired = await redis.set(lockKey, "1", { nx: true, ex: 10 });
if (!acquired) return;                                     // duplicate event mid-flight
try {
  await movePartnersToGroup({ workspaceId, programId, partnerIds: [partnerId],
                              userId: null, group: newGroup });
} finally {
  await redis.del(lockKey);                                // release even on failure
}
```
(:37-64 fresh read + skips; :112-132 lock + finally)

**Flow:** parse config · type guard (wrong action ⇒ skip) · require `identity.groupId` · fresh enrollment read (the orchestrator's snapshot may be stale after sibling workflows moved the partner) · same-target skip · `groupMoveDisabledAt` skip (a human moved/locked this partner — automation must not fight back) · evaluate conditions against `{aggregated metrics..., partnerGroup: programEnrollment.groupId}` (fresh value, NOT context's) · target group existence check with reward/discount ids selected (movePartnersToGroup swaps rewards atomically) · 10s NX dedup lock keyed (program, TARGET group, partner) so two workflows moving to the SAME target on one event collapse into one move · move inside try, unlock in finally.
**Invariant:** (1) decisions are made on freshly-read state, never the event-time snapshot — otherwise two condition-overlapping workflows both fire and the second undoes the first; (2) `userId: null` marks this as system-initiated (audit distinction); (3) the lock must be released in `finally` or a failed move wedges the key for its TTL and swallows legitimate retry moves; (4) skipping (not erroring) on disabled/same-target keeps the orchestrator's catch-and-continue log clean of noise.
**Probe:** `tests/workflows/move-group-workflow.test.ts` (789L, `describe.sequential`) pins: rule create/delete lifecycle (:29-142), disabled-workflow no-move (:144-227), conditions-not-met no-move (:225-291), plus between-range moves; deterministic probe: `grep -c 'groupMoveDisabledAt' apps/web/lib/api/workflows/move-group/execute.ts` = 2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "executeMoveGroupWorkflow", limit: 5 });
// → dub.apps.web.lib.api.workflows.move-group.execute.executeMoveGroupWorkflow @ move-group/execute.ts 11-133
```

## Verdict
Adopt the guard ladder (fresh-read → same-target → user-opt-out → evaluate → NX-dedup → move-under-lock-with-finally-unlock) for any auto-reassignment workflow. Adapt the lock store and the group/reward swap. Omit dub's reward-swap internals (`movePartnersToGroup` is its own seam).
