<!-- capsule-v2 -->
# Payout list read path — how does the payouts listing resolve tenant aliases, honor group NOT-IN filters, and project derived mode across a whole page?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What does GET /api/payouts guarantee for filters (partnerId vs tenantId, groupId exclusions) before any row shaping happens?

## getPayouts: shared where-builder → tenant alias → page-wide projection
**Path/Symbol:** `apps/web/lib/api/payouts/get-payouts.ts:buildProgramEnrollmentFilter` (:10-24), `buildPayoutWhere` (:26-49), `resolvePartnerId` (:53-75), `getPayouts` (:88-161). Count/export/detail variants have their own capsules.
**Signature:** `getPayouts({workspaceId, programId, filters})`; filter set `{groupId?, invoiceId?, partnerId?, tenantId?, status?, sortBy, sortOrder, page, pageSize}`.
**Data Shape:** `buildProgramEnrollmentFilter(groupId)` uses parseFilterValue so `-g1,g2` becomes `{notIn:[...]}` — group EXCLUSION rides the same param as inclusion; tenantId resolves through `tenantId_programId` unique and THROWS not_found when absent.

### Decisive source
```ts
return {
  groupId:
    groupFilter.sqlOperator === "NOT IN"
      ? { notIn: groupFilter.values }
      : { in: groupFilter.values },
};
...
const mode = payout.mode ?? getEffectivePayoutMode({
  payoutMode: program.payoutMode,
  payoutsEnabledAt: partner.payoutsEnabledAt });
return { ...payout, mode, traceId: payout.stripePayoutTraceId,
  partner: { ...partner, tenantId: programEnrollment.tenantId,
             groupId: programEnrollment.groupId }, user };
```
(:19-24, :151-160)

**Flow:** explicit partnerId always wins over tenantId (`if (!tenantId || partnerId) return partnerId`) → where = flat tenancy + optional joins via programEnrollment → findMany with skip/take from page/pageSize and sortBy/sortOrder passthrough → every row projected identically to the detail route (derived mode, traceId rename, enrollment fields folded onto partner).
**Invariant:** (1) tenant aliasing is an ACCESS path, not a filter — a bad tenant id errors rather than returning someone else's empty list; (2) exclusion filters must compose with tenancy INSIDE the enrollment relation, never as a post-filter, or pagination counts lie; (3) list rows carry the SAME derived shape as detail rows so clients render one component.
**Probe:** deterministic probe: `grep -n 'NOT IN' apps/web/lib/api/payouts/get-payouts.ts` = :21; `grep -c 'resolvePartnerId' apps/web/lib/api/payouts/get-payouts.ts` = 2. No upstream unit suite covers this file directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "buildProgramEnrollmentFilter", limit: 5 });
```

## Verdict
Adopt tenant-alias access paths, relation-scoped exclusion filters, and uniform row projection. Adapt filter grammar. Omit groups if absent in your domain.
