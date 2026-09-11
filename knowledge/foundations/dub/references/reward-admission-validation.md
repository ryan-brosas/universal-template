<!-- capsule-v2 -->
# Reward admission validation — per-event shape gates and the referral trigger taxonomy

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** What combinations of event × type × amount fields are legal when creating/updating a reward?

## validateReward's four-section gate
**Path/Symbol:** `apps/web/lib/api/rewards/validate-reward.ts:validateReward` (:13-213); trigger tables `apps/web/lib/partner-referrals/constants.ts:PARTNER_REFERRAL_{PERCENTAGE,FLAT}_TRIGGERS` (:32-39).
**Signature:** `validateReward(reward: Partial<z.infer<typeof createOrUpdateRewardSchema>>): void` — throws `DubApiError{code:"bad_request"}` on every violation.
**Data Shape:** click/lead = flat-cents only; sale = flat XOR percentage; referral = config-driven with type-specific triggers; modifiers validated whenever present; spend-limit pair all-or-nothing.

### Decisive source
```ts
if (hasSpendLimitAmount !== hasSpendLimitInterval) {
  throw new DubApiError({
    code: "bad_request",
    message: `Both "spendLimitAmount" and "spendLimitInterval" are required together. Provide both fields or omit both.`,
  });
}
```
(validate-reward.ts :204-212)

**Flow (source order):** CLICK/LEAD (:16-38): percentage forbidden outright; amountInCents REQUIRED; amountInPercentage forbidden → SALE (:40-70): amountInCents XOR amountInPercentage (both-set and neither-set both throw), flat⇒cents / percentage⇒percentage consistency → REFERRAL (:72-147): modifiers FORBIDDEN; config must parse via referralRewardConfigSchema else generic message; percentage ⇒ percentage-only + trigger ∈ PARTNER_REFERRAL_PERCENTAGE_TRIGGERS (`saleRecorded`, `commissionEarned` — derived from PARTNER_REFERRAL_TRIGGER_CONFIG keys :2-19); flat ⇒ cents-only + trigger ∈ FLAT_TRIGGERS (`partnerApproved`, `commissionThreshold`) → MODIFIERS (:149-202): per-modifier indexed messages ("Modifier N:") requiring type, exactly one amount field, and type/field consistency → SPEND LIMIT (:204-212): presence-XOR throw.
**Invariant:** error MESSAGES are part of the contract (frozen UI copy surfaced in program settings) — port them verbatim; the referral trigger allowlists are DERIVED from a verb/basis config object so new triggers flow into validation automatically; modifier parse failure at the zod layer is silently tolerated here (validation only runs on successful parses) because schema-level errors surface elsewhere.
**Probe:** deterministic probes (repo root): `grep -n 'Percentage rewards are not allowed' apps/web/lib/api/rewards/validate-reward.ts` → :21; `grep -c 'DubApiError' apps/web/lib/api/rewards/validate-reward.ts` → 22; `grep -n 'hasSpendLimitAmount !== hasSpendLimitInterval' apps/web/lib/api/rewards/validate-reward.ts` → :207; `grep -n 'Modifier ${index + 1}' apps/web/lib/api/rewards/validate-reward.ts` → :159/:169/:179; `sed -n '32,39p' apps/web/lib/partner-referrals/constants.ts` shows both Object.keys derivations.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "validateReward", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-section gate incl. verbatim messages and derived trigger allowlists. Adapt DubApiError to host envelope. Omit nothing.
