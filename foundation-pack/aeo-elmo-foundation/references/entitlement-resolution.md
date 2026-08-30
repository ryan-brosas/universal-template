<!-- capsule-v2 -->
# Entitlement resolution — how do subscriptions, overrides, and mode flags become run limits?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How does the worker learn what an org may run, and why does non-cloud mode bypass the DB entirely?

## Two queries + healthiest-subscription pick
**Path/Symbol:** `packages/lib/src/entitlements/service.ts:STATUS_RANK` (L32–41), `selectRelevantSubscription` (L47–55), `getOrgBillingStates` (L114–150), `getOrgEntitlementsMap` (L170–176); pure resolver in `packages/config/src/entitlements.ts`.
**Signature:** `getOrgBillingStates(orgIds: string[], options?: {mode?, now?}): Map<string, OrgBillingState>`; `selectRelevantSubscription(rows): SubscriptionRow | null`.
**Data Shape:** status rank active(0) > trialing > past_due > paused > unpaid > incomplete > incomplete_expired > canceled(7), unknown = 99; ties broken by latest periodEnd. Settings row contributes `premiumAddonQuantity` + JSON `entitlementOverrides` (parsed/validated by config).

### Decisive source
```ts
// Outside cloud mode this never touches the database — the first line resolves
// to UNLIMITED_ENTITLEMENTS, which is what keeps local/demo/whitelabel
// provably unaffected by everything built on top of this.
if (mode !== "cloud") { for (const orgId of orgIds) result.set(orgId, UNLIMITED_STATE); return result; }
```
Batching contract: "Every requested org gets an entry, so callers never have to distinguish 'no row' from 'not asked for'." Single-org accessors funnel through the batch variant — "one query shape, one place that decides which subscription row wins".

**Flow:** maintenance sweep calls getOrgEntitlementsMap once for all enabled brands' orgs; per-prompt firing calls getOrgEntitlements; both feed resolvePromptRunPlan. The pure resolver (config) turns `{subscription, premiumAddonQuantity, overrides, now}` into Entitlements incl. trial expiry.
**Invariant:** non-cloud ⇒ unlimited is a PROVABLE isolation property (first branch), not scattered conditionals; entitlements are read fresh per decision so downgrades apply without touching queued jobs.
**Probe:** `packages/lib/src/entitlements/service.test.ts` + `guards.test.ts` + `packages/config/src/entitlements.test.ts` / `plans.test.ts` (GREEN in probe run).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "selectRelevantSubscription getOrgBillingStates UNLIMITED_ENTITLEMENTS STATUS_RANK", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mode-first short-circuit + ranked subscription pick + always-populate-map contract; adapt rank table to your billing statuses; omit guards module if you have no metered write paths.
