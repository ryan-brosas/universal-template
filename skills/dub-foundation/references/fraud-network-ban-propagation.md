<!-- capsule-v2 -->
# Network-level ban propagation — one program's ban becomes partnerCrossProgramBan events in every OTHER enrolled program whose rule is enabled

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** When program A bans a partner, how do other programs learn — and who decides which of them receive the alert?

## Cross-program enrollment sweep with per-program opt-out
**Path/Symbol:** `apps/web/lib/api/fraud/report-network-level-ban.ts:reportNetworkLevelBan` (:12-91).
**Signature:** `async function reportNetworkLevelBan({ partnerId, programId /* issuer */, bannedReason, bannedAt })` — no return value consumed.
**Data Shape:** events carry `sourceProgramId = issuing programId` (persisted on FraudEvent, schema :64) + `metadata {bannedReason, bannedAt}`; hash identity for this type = sourceProgramId (see fraud-event-hash-identity).

### Decisive source
```ts
let affectedProgramEnrollments = await prisma.programEnrollment.findMany({
  where: { partnerId, programId: { not: programId },            // EVERY OTHER program
           status: { notIn: INACTIVE_ENROLLMENT_STATUSES },
           riskMonitoringDisabledAt: null },
  select: { ..., program: { select: { fraudRules: true } } } });
affectedProgramEnrollments = affectedProgramEnrollments.filter((enrollment) =>
  isFraudRuleEnabled({ fraudRules: enrollment.program.fraudRules,
                       ruleType: FraudRuleType.partnerCrossProgramBan }));
const { affectedGroups } = await createFraudEvents(affectedProgramEnrollments.map((e) => ({
  programId: e.programId, partnerId, type: "partnerCrossProgramBan",
  sourceProgramId: programId, metadata: { bannedReason, bannedAt } })));
await Promise.allSettled([ holdPendingCommissions(affectedGroups),
                            holdProcessedCommissions(affectedGroups) ]);
```
(report-network-level-ban.ts :132-199 condensed)

**Flow:** find all ACTIVE, monitoring-enabled enrollments EXCLUDING the banning program → drop programs with the crossProgramBan rule disabled → one event per remaining enrollment → createFraudEvents (group continuity per receiving program) → immediate best-effort commission holds in each receiving program.
**Invariant:** (1) the ISSUING program never receives its own event; (2) propagation is OPT-OUT per receiving program via its fraud-rule row (absence-of-row = ON, matching the merge capsule); (3) inactive or risk-monitoring-disabled enrollments are skipped BEFORE the rule filter; (4) holds fire IMMEDIATELY in receiving programs (unlike conversion-time detection where holds happen in the same request as commission creation) because a confirmed ban is high-severity; (5) `sourceProgramId` preserves provenance so reviewers see WHICH program issued the ban.
**Probe:** anchored at dub repo root: `grep -c 'not: programId' apps/web/lib/api/fraud/report-network-level-ban.ts` = **1**; `grep -c 'sourceProgramId: programId' apps/web/lib/api/fraud/report-network-level-ban.ts` = **1**. Direct tests: none isolated (recorded caveat); ban flow exercised indirectly through E2E suites that ban partners.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "reportNetworkLevelBan", limit: 5 });
```

## Verdict
Adopt opt-out network propagation with source attribution and immediate holds. Adapt whether your network trusts single-program bans blindly. Omit nothing in the filter order.
