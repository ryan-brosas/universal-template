<!-- capsule-v2 -->
# Partner application risk surface — four synchronous profile checks plus pending partner-level group lookups, ranked by severity config

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** At application-review time, how are partner-profile risks computed WITHOUT the rule engine, and how do stored groups override them?

## Read-time risk matrix: DB groups for the two high rules, pure functions for the rest
**Path/Symbol:** `apps/web/lib/api/fraud/get-partner-application-risks.ts:getPartnerApplicationRisks` (:11-56) + `lib/get-highest-severity.ts` (:4-22) + `rules/check-partner-email-{masked,domain-mismatch}.ts` + `rules/check-partner-no{,-verified}-social-links.ts`.
**Signature:** `async function getPartnerApplicationRisks({ program, partner }): Promise<{ risksDetected: Partial<Record<ExtendedFraudRuleType, boolean>>; riskSeverity: FraudSeverity | null }>`.
**Data Shape:** `risksDetected` is a FULL six-key record (booleans may be false); `riskSeverity` = max rank over triggered rules using `FRAUD_SEVERITY_CONFIG` ranks low=0/medium=1/high=2, null when nothing triggered.

### Decisive source
```ts
const fraudGroups = await prisma.fraudEventGroup.findMany({
  where: { programId, partnerId, status: "pending",
           type: { in: ["partnerCrossProgramBan", "partnerDuplicateAccount"] } } });
const risksDetected = {
  partnerCrossProgramBan: fraudGroups.some((g) => g.type === "partnerCrossProgramBan"),
  partnerDuplicateAccount: fraudGroups.some((g) => g.type === "partnerDuplicateAccount"),
  partnerEmailDomainMismatch: checkPartnerEmailDomainMismatch(partner), // email domain ≠ website-platform domain
  partnerEmailMasked: checkPartnerEmailMasked(partner),                 // domain === "privaterelay.appleid.com"
  partnerNoSocialLinks: checkPartnerNoSocialLinks(partner),             // no platform identifier with trim().length > 0
  partnerNoVerifiedSocialLinks: checkPartnerNoVerifiedSocialLinks(partner), // no platform.verifiedAt != null
};
const triggeredRules = FRAUD_RULES.filter((rule) => risksDetected[rule.type] === true);
const riskSeverity = getHighestSeverity(triggeredRules);
```
(get-partner-application-risks.ts :18-50 condensed)

**Flow:** one pending-group query covers both partner-level types → two DB-derived booleans → four pure synchronous checks over `{email, country, platforms}` (domain-mismatch normalizes www+case on both sides and returns false when email/website missing; masked is a single Apple-relay domain equality; the two social checks differ by VERIFICATION: any non-blank identifier vs any `verifiedAt != null`) → severity ranking via catalog metadata (`severity` lives on FRAUD_RULES entries, not in the check functions).
**Invariant:** (1) the two HIGH-severity rules are STATE-BACKED (pending groups) while the four LOW/MEDIUM are COMPUTED — a resolved ban does not show as current risk but stays in history; (2) all four profile checks FAIL-CLOSED-to-false on missing data (no email/no website/no platforms ⇒ not risky) — they measure verifiability gaps, not proof of abuse; (3) severity comes from ONE static config so UI badges and this API can never drift.
**Probe:** anchored at dub repo root: `grep -c 'privaterelay.appleid.com' apps/web/lib/api/fraud/rules/check-partner-email-masked.ts` = **1**; `grep -c 'verifiedAt != null' apps/web/lib/api/fraud/rules/check-partner-no-verified-social-links.ts` = **1**; `grep -c 'trim().length > 0' apps/web/lib/api/fraud/rules/check-partner-no-social-links.ts` = **1**; `grep -c 'rank:' apps/web/lib/api/fraud/constants.ts` = **4** (low/medium/high + none? — 4 rank literals incl. the config map's entries); `grep -c 'in: \["partnerCrossProgramBan", "partnerDuplicateAccount"\]' apps/web/lib/api/fraud/get-partner-application-risks.ts` = **1**. Direct tests: none isolated (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getPartnerApplicationRisks", limit: 5 });
```

## Verdict
Adopt the split: state-backed booleans for high-severity rules, pure profile heuristics for soft signals, single-source severity ranking. Adapt which rules are state-backed to your review workflow. Omit the UI color fields of FRAUD_SEVERITY_CONFIG.
