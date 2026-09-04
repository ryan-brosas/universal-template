<!-- capsule-v2 -->
# AI-usage credit reserve/refund — how do you enforce a metered quota atomically without a read-modify-write race?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1` (drift pass; `reserveAIUsageCredit`/`refundAIUsageCredit` are new). **Question:** What is the correct primitive for spend-one-credit-then-refund-on-failure quota enforcement?

## Conditional atomic increment + bounded decrement
**Path/Symbol:** `apps/web/lib/api/links/usage-checks.ts:reserveAIUsageCredit` (:54-77) and `refundAIUsageCredit` (:79-93).
**Signature:** `reserveAIUsageCredit(workspace: Pick<WorkspaceWithUsers,"id"|"aiLimit"|"plan"|"planPeriod">): Promise<void>` (throws); `refundAIUsageCredit(workspaceId: string): Promise<void>`.
**Data Shape:** quota lives as counters on the Project row (`aiUsage`, `aiLimit`); the check is `aiUsage < aiLimit`.

### Decisive source
```ts
const count = await prisma.$executeRaw`
  UPDATE Project
  SET aiUsage = aiUsage + 1
  WHERE id = ${workspaceId}
    AND aiUsage < aiLimit
`;
if (count === 0) {
  throw new DubApiError({ code: "forbidden", message: exceededLimitError({...type:"AI"}) });
}

export async function refundAIUsageCredit(workspaceId: string) {
  await prisma.project.updateMany({
    where: { id: normalizeWorkspaceId(workspaceId), aiUsage: { gt: 0 } },
    data: { aiUsage: { decrement: 1 } },
  });
}
```

**Flow:** consume = single conditional UPDATE whose WHERE contains the limit test — affected-rows 0 means over-quota (throw forbidden with the plan-aware upgrade message); refund later = decrement guarded by `gt: 0`. The read-side twin (`throwIfAIUsageExceeded`) stays a plain compare for cheap pre-checks in list endpoints, but the AUTHORITATIVE gate at spend time is the conditional UPDATE.
**Invariant:** the quota decision and the increment must be ONE statement — a separate SELECT then UPDATE double-spends under concurrency; `$executeRaw` is used because Prisma's updateMany can't express `SET x = x + 1 WHERE x < limit` with an affected-count that distinguishes "row missing" from "quota full" here. Refund MUST be floored at zero (`gt: 0`) so retries/failures can't drive usage negative and mint free credits. Workspace ids pass through `normalizeWorkspaceId` on both paths.
**Probe:** no upstream unit test pins these two helpers directly — coverage caveat; deterministic probe: with `aiUsage == aiLimit`, `reserveAIUsageCredit` throws forbidden AND `aiUsage` is unchanged; after one refund on a fresh workspace, usage never drops below 0.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "reserveAIUsageCredit refundAIUsageCredit", limit: 6 });
// → lib.api.links.usage-checks.reserveAIUsageCredit @ usage-checks.ts 54-77
```

## Verdict
Adopt the single-statement conditional-increment gate plus zero-floored refund for any metered resource. Adapt the counter columns and error envelope to your stack. Omit the raw-SQL form only if your ORM expresses the same conditional increment atomically.
