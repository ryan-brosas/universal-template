<!-- capsule-v2 -->
# Payout count & single-payout read — how do the dashboard's status tabs get their numbers and how does the detail row expose mode/trace without leaking internal columns?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What does /api/payouts/count return in each mode, and what does the [payoutId] route derive that storage doesn't hold?

## payouts/count + payouts/[payoutId]
**Path/Symbol:** `apps/web/app/(ee)/api/payouts/count/route.ts:GET` (:71-144); `apps/web/app/(ee)/api/payouts/[payoutId]/route.ts:GET` (:14-61).
**Signature:** count params `{status?, partnerId?, groupId?, groupBy?, eligibility?, invoiceId?}`; `eligibility:"eligible"` swaps the plain where for getPayoutEligibilityFilter (the SAME predicate as claiming).
**Data Shape:** groupBy=status ⇒ array over ALL enum statuses zero-filled; else single `{count, amount, status: status ?? "all"}`; detail response = PayoutResponseSchema with `mode` derived via getEffectivePayoutMode when stored null and `partner.tenantId` folded from the enrollment join.

### Decisive source
```ts
const { partner, programEnrollment, ...rest } = payout;
const mode = rest.mode ?? getEffectivePayoutMode({
  payoutMode: program.payoutMode,
  payoutsEnabledAt: partner.payoutsEnabledAt });
return NextResponse.json(PayoutResponseSchema.parse({ ...rest, mode,
  traceId: rest.stripePayoutTraceId,
  partner: { ...partner, tenantId: programEnrollment.tenantId } }));
```
([payoutId]/route.ts :184-203)

**Flow:** count builds one where object; eligibility flag REPLACES it with the shared filter so tab badges can show "what you could pay right now"; status tabs use groupBy + zero-fill. Detail: findUnique scoped by id+programId → not_found error → strip join objects → derive mode/trace/tenantId → zod-parse so internal columns (stripePayoutTraceId raw name etc.) are projected exactly once.
**Invariant:** (1) the "eligible" badge and the actual claim share ONE predicate — a badge that lies about payability breaks operator trust; (2) derived fields are computed at READ time so schema evolution (adding mode later) never requires backfills.
**Probe:** deterministic probe: `grep -c 'getPayoutEligibilityFilter' 'apps/web/app/(ee)/api/payouts/count/route.ts' 'apps/web/app/(ee)/api/payouts/[payoutId]/route.ts' | paste -sd' '` shows 1+0 sites; `grep -n 'status ?? "all"' 'apps/web/app/(ee)/api/payouts/count/route.ts'` = :82. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "PayoutStatus", limit: 8 });
```

## Verdict
Adopt shared-predicate badges and read-time derivation. Adapt schemas. Omit zero-filling if your UI handles absent buckets.
