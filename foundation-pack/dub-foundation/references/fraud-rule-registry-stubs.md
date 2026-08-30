<!-- capsule-v2 -->
# Fraud rule registry & defineFraudRule contract — how are rule types bound to evaluators, and what happens to enum members with no real implementation?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How do I add or port a fraud rule, and why do two Prisma enum values resolve to stubs that never trigger?

## Registry keyed by FraudRuleType with explicit never-trigger stubs
**Path/Symbol:** `apps/web/lib/api/fraud/execute-fraud-rule.ts:FRAUD_RULES_REGISTRY` (:17-27) + `define-fraud-rule.ts:defineFraudRule` (:5-17).
**Signature:** `async function executeFraudRule<T extends FraudRuleType>({ type, context, config }: { type: T; context: unknown; config?: unknown }): Promise<FraudTriggeredRule>`.
**Data Shape:** `FRAUD_RULES_REGISTRY: Record<FraudRuleType, ReturnType<typeof defineFraudRule>>` — every Prisma enum member must have an entry (TS Record totality). Four real rules map to imported check functions; the two partner-level rules (`partnerCrossProgramBan`, `partnerDuplicateAccount`) get `defineFraudRuleStub(type)` entries whose evaluate is `async () => ({ triggered: false })`.

### Decisive source
```ts
// TS trick: these rules are evaluated elsewhere, so we stub their registry entry.
const defineFraudRuleStub = (type: FraudRuleType) =>
  ({ type, evaluate: async () => ({ triggered: false }) });

const FRAUD_RULES_REGISTRY = {
  customerEmailMatch: checkCustomerEmailMatch,
  customerEmailSuspiciousDomain: checkCustomerEmailSuspicious,
  referralSourceBanned: checkReferralSourceBanned,
  paidTrafficDetected: checkPaidTrafficDetected,
  partnerCrossProgramBan: defineFraudRuleStub("partnerCrossProgramBan"),
  partnerDuplicateAccount: defineFraudRuleStub("partnerDuplicateAccount"),
};
...
const rule = FRAUD_RULES_REGISTRY[type];
if (!rule) throw new Error(`Unknown fraud rule: ${type}`);
return await rule.evaluate(context, config);
```
(execute-fraud-rule.ts :9-45 condensed)

**Flow:** `defineFraudRule` is a typed identity factory (`{...rule, configSchema}` — carries optional zod `configSchema` + `defaultConfig` alongside evaluate) → registry lookup by enum → missing entry throws loud → delegate `(context, config)`. The partner-level detections do NOT flow through this registry: `detectDuplicateIdentityFraud`/`detectDuplicatePayoutMethodFraud`/`reportNetworkLevelBan`/`detectAndRecordFraudApplication` call `createFraudEvents` directly (they are event-driven detectors, not per-conversion predicates).
**Invariant:** (1) the stub comment is the CONTRACT: partner-level rules must stay registered-but-inert here so the conversion loop can never double-fire them; (2) a new FraudRuleType enum member REQUIRES a registry entry (Record totality fails compile otherwise) — add both sides in lockstep; (3) `context`/`config` enter evaluate as `unknown` — each rule owns its own validation (zod configSchema parse inside the check), so registry dispatch adds zero safety.
**Probe:** anchored at dub repo root: `grep -c 'defineFraudRuleStub' apps/web/lib/api/fraud/execute-fraud-rule.ts` = **3** (helper def + two stub entries); `grep -c 'Unknown fraud rule' apps/web/lib/api/fraud/execute-fraud-rule.ts` = **1**. Direct tests: none for this file (recorded caveat); the six E2E flows in `tests/fraud/index.test.ts` cover all four real rules through HTTP.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "executeFraudRule", limit: 5 });
```

## Verdict
Adopt the exhaustive-registry-with-stub pattern (enum-driven dispatch that stays total without fake implementations). Adapt the FraudRuleType enum and per-rule config schemas. Omit nothing in the dispatch path.
