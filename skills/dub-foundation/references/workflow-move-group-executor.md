<!-- capsule-v2 -->
# Move-group workflow executor — fresh-read guards, condition evaluation, and the NX dedup lock around a single-partner move

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How does the durable workflow engine invoke movePartnersToGroup for one partner without double-moving or overriding an admin's opt-out?

## executeMoveGroupWorkflow
**Path/Symbol:** `apps/web/lib/api/workflows/move-group/execute.ts:executeMoveGroupWorkflow` (:11-133).
**Signature:** `executeMoveGroupWorkflow({workflow: Workflow, context: WorkflowContext}): Promise<void>` — silent console-log returns, never throws on business skips.
**Data Shape:** action.data = `{groupId: newGroupId}`; context.identity = {workspaceId, programId, partnerId, groupId?}; metrics.aggregated supplies totalLeads/totalConversions/totalSaleAmount/totalCommissions.

### Decisive source
```ts
// Prevents duplicate moves when a workflow with matching conditions
// are triggered by the same event.
const lockKey = `workflow:moveGroup:${programId}:${newGroupId}:${partnerId}`;
const acquired = await redis.set(lockKey, "1", { nx: true, ex: 10 });

if (!acquired) {
  console.log(`Partner ${partnerId} move already in progress. Skipping..`);
  return;
}

try {
  await movePartnersToGroup({
    workspaceId,
    programId,
    partnerIds: [partnerId],
    userId: null,
    group: newGroup,
  });
} finally {
  await redis.del(lockKey);
}
```
(execute.ts :112-132)

**Flow:** parse config → action-type guard (wrong type ⇒ skip) → identity.groupId present? → FRESH programEnrollment read (not the trigger-time context): already in target group ⇒ skip; groupMoveDisabledAt set ⇒ skip (admin opt-out honored even though rules matched) → build workflow attribute context from aggregated metrics + CURRENT group → evaluateWorkflowConditions (silent-false evaluator per pass-4 capsule) → load target group with all five reward/discount id columns → token-less NX lock ex:10 → movePartnersToGroup([partnerId], userId:null) → finally del lock.
**Invariant:** the fresh read is the correctness anchor — trigger context can be stale by minutes; userId null marks this as workflow-initiated so movePartnersToGroup attributes the activity log to the workspace OWNER (its own fallback); the 10s lock TTL only needs to outlive the synchronous DB write since the heavy fan-out is waitUntil-deferred inside movePartnersToGroup. Complements pass-5 `move-group-guard-ladder` (route-side) — this is the executor-side twin.
**Probe:** deterministic probes (repo root): `grep -n 'workflow:moveGroup:' apps/web/lib/api/workflows/move-group/execute.ts` → :114; `grep -n 'nx: true, ex: 10' apps/web/lib/api/workflows/move-group/execute.ts` → :115; `grep -n 'groupMoveDisabledAt' apps/web/lib/api/workflows/move-group/execute.ts` → :47/:59; `grep -n 'userId: null' apps/web/lib/api/workflows/move-group/execute.ts` → :127.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "executeMoveGroupWorkflow", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fresh-read revalidation before acting, opt-out honoring inside automated flows, and short-TTL NX locks released in finally. Adapt metrics shape. Omit nothing.
