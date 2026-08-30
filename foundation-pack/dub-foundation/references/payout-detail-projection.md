<!-- capsule-v2 -->
# Payout detail projection — how does the single-payout API derive mode/trace/tenant at read time, and why is the zod parse the security boundary?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What does /api/payouts/[payoutId] compute that storage doesn't hold, and how are internal columns kept out of responses?

## payouts/[payoutId] route
**Path/Symbol:** `apps/web/app/(ee)/api/payouts/[payoutId]/route.ts:GET` (:14-61).
**Signature:** GET with `{payoutId}` scoped by programId; include enrollment+partner+user.
**Data Shape:** destructures `{partner, programEnrollment, ...rest}` then re-projects through PayoutResponseSchema: mode derived when null, `traceId ← rest.stripePayoutTraceId`, partner gains `tenantId` from the enrollment — internal column names never surface.

### Decisive source
```ts
const { partner, programEnrollment, ...rest } = payout;
const mode = rest.mode ?? getEffectivePayoutMode({
  payoutMode: program.payoutMode, payoutsEnabledAt: partner.payoutsEnabledAt });
return NextResponse.json(PayoutResponseSchema.parse({
  ...rest, mode,
  traceId: rest.stripePayoutTraceId,
  partner: { ...partner, tenantId: programEnrollment.tenantId } }));
```
(:184-203)

**Flow:** findUnique by (id, programId) → not_found DubApiError → destructure joins → derive → schema-parse. The parse is the whitelist: any future Prisma column appears in `rest` but is DROPPED unless PayoutResponseSchema grows a field.
**Invariant:** (1) read-time derivation keeps legacy rows correct without migrations; (2) zod-parse-as-projection means accidental column additions can't leak — porters who serialize `rest` directly lose this guarantee.
**Probe:** deterministic probe: `grep -n 'PayoutResponseSchema.parse' 'apps/web/app/(ee)/api/payouts/[payoutId]/route.ts'` = :194. No upstream unit suite covers this route directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getEffectivePayoutMode", limit: 5 });
```

## Verdict
Adopt derive-at-read + parse-as-whitelist for any entity with evolved schemas. Adapt field names. Omit nothing else.
