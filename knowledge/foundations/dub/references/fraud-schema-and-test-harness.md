<!-- capsule-v2 -->
# Fraud data model & E2E test harness — the four-table Prisma shape, the unique constraint behind rule overrides, and the poll-until-event test helper

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What does the persistence schema guarantee, and how do the integration tests observe asynchronously-created fraud events?

## FraudRule / FraudEventGroup / FraudEvent / FraudAlert with deliberate index placement
**Path/Symbol:** `apps/web/prisma/schema/fraud.prisma` (whole file :1-112).
**Signature:** `model FraudRule @@unique([programId, type])`; `FraudEventGroup @@index([programId, partnerId, type, status])` + `@@index(lastEventAt)`; `FraudEvent @@index(hash)` + `@@index([programId, partnerId, customerId])`.
**Data Shape:** statuses `{pending, resolved, expired}`; group carries denormalized `lastEventAt`/`eventCount` counters; event is the immutable fact row (hash + metadata + optional link/customer/event/sourceProgram ids); FraudAlert is a SEPARATE review queue (pending/confirmed/dismissed) not joined to groups.

### Decisive source
```prisma
enum FraudRuleType { customerEmailMatch  customerEmailSuspiciousDomain  referralSourceBanned
                     paidTrafficDetected  partnerCrossProgramBan  partnerDuplicateAccount }
model FraudRule {
  ...
  config     Json?
  disabledAt DateTime?
  @@unique([programId, type])      // one override row per program+rule → upsert-able settings
}
model FraudEventGroup {
  status FraudEventStatus @default(pending)
  ... @@index([programId, partnerId, type, status])   // THE continuity lookup + release surveys
}
```
(fraud.prisma :7-54 condensed)

**Flow:** detection writes events under pending groups; UI reads via `/fraud/groups` + `/fraud/events` routes filtered by status/type/partner/customer; resolution/expiry flips group status; hash index backs dedup lookups. **Test harness:** `tests/utils/verify-fraud-event.ts:verifyFraudEvent` (:51-124) resolves customerId from externalId, then POLLS `/fraud/events?customerId&type=` every VITEST_POLL_INTERVAL_MS until VITEST_TEST_TIMEOUT_MS, asserting the FULL event shape with `toStrictEqual` (`createdAt: expect.any(String)`, partner/customer objectContaining, optional metadata) — because event creation is asynchronous relative to `/track/lead`.
**Invariant:** (1) the `@@unique([programId,type])` makes program overrides a natural upsert target (settings UI never duplicates rows); (2) group counters are DENORMALIZED by design — list views never aggregate events; (3) FraudEvent rows are append-only facts: no status of their own, lifecycle lives on the group; (4) tests must POLL (not await) since detection happens inside the lead-ingestion pipeline after response.
**Probe:** anchored at dub repo root: `grep -c '@@unique(\[programId, type\])' apps/web/prisma/schema/fraud.prisma` = **1**; `grep -A3 'enum FraudEventStatus' apps/web/prisma/schema/fraud.prisma | grep -c 'pending'` = **1**; `grep -c 'toStrictEqual' apps/web/tests/utils/verify-fraud-event.ts` = **1**; `ls apps/web/tests/fraud/` = fraud-groups.test.ts + index.test.ts. Direct tests: both suites are REAL runner files (vitest IntegrationHarness against a live stack: PG+Redis+QStash cloud deps — standing offline block recorded since pass 4); fraud-groups pins list/filter/retrieve semantics incl. schema parse (:14-120+).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "FraudEventGroup", limit: 5 });
```

## Verdict
Adopt the schema split (mutable group lifecycle vs immutable hashed events) and the poll-based async assertion pattern. Adapt id prefixes and enum sets. Omit FraudAlert internals until a review-workflow port needs them.
