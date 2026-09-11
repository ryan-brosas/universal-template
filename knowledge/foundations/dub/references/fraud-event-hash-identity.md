<!-- capsule-v2 -->
# Fraud event hash identity & metadata sanitization — which fields make a fraud event unique per rule type, and why are three metadata keys deleted before persistence?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How is "same fraud event already recorded" decided, and what identity fields does each rule type contribute to that decision?

## Per-type identity projection + sorted-key sha256(24) hash
**Path/Symbol:** `apps/web/lib/api/fraud/utils.ts:createFraudEventHash` (:49-67) + `getIdentityFieldsForFraudEvent` (:71-109) + `sanitizeFraudEventMetadata` (:112-126).
**Signature:** `createFraudEventHash(e: Pick<CreateFraudEventInput,"type"|"programId"|"partnerId"|"customerId"|"sourceProgramId"|"metadata">): string`; `createHashKey = sha256(raw).digest("base64url").slice(0, 24)`.
**Data Shape:** raw string = `[programId, partnerId, type, normalizedIdentityFields].map(p => p!.toLowerCase()).join("|")` where normalizedIdentityFields = sorted `key:value` pairs of the type-specific identity record joined by `|`.

### Decisive source
```ts
switch (type) {
  case "customerEmailMatch":
  case "customerEmailSuspiciousDomain":
  case "referralSourceBanned":
  case "paidTrafficDetected":
    if (!customerId) throw new Error(`customerId is required for ${type} fraud rule.`);
    return { customerId };                       // customer-level: identity IS the customer
  case "partnerDuplicateAccount":
    return { duplicatePartnerId: eventMetadata?.duplicatePartnerId };   // the OTHER account
  case "partnerCrossProgramBan":
    if (!sourceProgramId) throw new Error(`sourceProgramId is required for ${type} fraud rule.`);
    return { sourceProgramId };                  // the banning program
}
```
(utils.ts :79-108 condensed)

**Flow:** `normalizeEmail` (lower/trim → strip `+tag` for ALL domains → strip dots only for gmail.com/googlemail.com :20-42) feeds rule evaluation, not the hash — but both share the dedup intent. Hash consumers: `create-fraud-events.ts` maps every event through `createFraudEventHash`, dedupes in-memory via Map, then queries existing rows with same hash whose **group is still pending**. `sanitizeFraudEventMetadata` deletes exactly `duplicatePartnerId`, `payoutMethodHash`, `cryptoWalletAddress` — the PII-ish identity fields that ARE the dedup key and must not be duplicated into stored metadata; returns undefined when nothing remains.
**Invariant:** (1) two events differing ONLY in link/customer-email/event-id hash IDENTICAL when customerId matches — repeat conversions by the same customer never spawn duplicate pending events; (2) missing required identity fields THROW inside hashing (fail-closed), so a caller can't silently create un-deduplicatable events; (3) everything lowercases before hashing — case differences never split identity; (4) sanitized keys must stay in lockstep with what detectors write into metadata (`duplicatePartnerId` from both duplicate detectors, `payoutMethodHash`/`cryptoWalletAddress` from payout-method detection).
**Probe:** anchored at dub repo root: `grep -c 'slice(0, 24)' apps/web/lib/api/fraud/utils.ts` = **1**; `grep -o 'duplicatePartnerId' apps/web/lib/api/fraud/utils.ts | wc -l` = **4**; `grep -cE 'delete sanitized\.' apps/web/lib/api/fraud/utils.ts` = **3**; `grep -c 'customerId is required' apps/web/lib/api/fraud/utils.ts` = **1**. Direct tests: no unit suite for utils.ts (recorded caveat); dedup semantics observable via E2E `verifyFraudEvent` polling helper (`tests/utils/verify-fraud-event.ts`, single `toStrictEqual` shape pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createFraudEventHash", limit: 5 });
```

## Verdict
Adopt per-rule-type identity projection with fail-closed required-field throws, plus pre-persist sanitization keyed to detector-written fields. Adapt hash truncation length and email normalizer rules to host policy. Omit base64url specifics if your DB prefers hex.
