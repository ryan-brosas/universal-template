<!-- capsule-v2 -->
# Product-feature limit gates — where do maxDocs/maxShares/maxWorkspaces/assistant-call limits actually get enforced?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How do billing-account features turn into 402/403/429s with machine-usable `limit` payloads, and how do usage counters reset?

## Effective features checked inline at each mutation with structured ApiError.limit; usage Limits rows self-reset on billing-period rollover at read time
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `_checkRoomForAnotherDoc` (:5192–5220), workspace limit in `addWorkspace` (:1592–1606), `_restrictShares` (:5136–5164) + `_restrictAllDocShares` (:5171–5189), readonly downgrades (:1104–1110), `increaseUsage` (:3018–3081), `_getOrCreateLimitAndReset` (:3747–3822), invite/billing-manager caps (`_failIfTooManyNewUserInvites` :4210–4244, `_failIfTooManyBillingManagers` :4186–4208).
**Signature:** `_restrictShares(role|null, limit, before: User[], after: User[], checkChange: boolean, kind, features)` — throws only when NEW shares would exceed (`after.some(user => !existingUserIds.has(user.id))`).
**Data Shape:** Error payload contract: `{limit: {quantity, subquantity?, maximum, value, projectedValue}, tips: [{action: "upgrade"|"add-members"|"manage", message}]}`; assistant-limit 429 adds `tips[].action = stripeCustomerId ? "manage" : "upgrade"`.

### Decisive source
```ts
const billingOk = workspace.org.billingAccount.inGoodStanding;
if (!billingOk) {
  throw new ApiError("Site is in readonly mode due to billing issues", 429);
}
if (features.maxDocsPerOrg !== undefined) {
  ...
  if (count >= features.maxDocsPerOrg) {
    throw new ApiError("No more documents permitted", 403, {
      limit: { quantity: "docs", maximum: features.maxDocsPerOrg,
               value: count, projectedValue: count + 1 } });
```
Lazy period reset:
```ts
// We can only reset the limit if we know the billing period end date, and this is
// not a free plan.
if (existing.billingAccount.status?.currentPeriodEnd && ... && !isFreePlan(...)) {
  const expected = expectedResetDate(startDate, endDate, timestamp.getTime());
  if (expected) {
    const wasResetOk = existing.resetAt && expected < existing.resetAt.getTime();
    if (!wasResetOk) { existing.usage = 0; existing.resetAt = timestamp; ... }
```

**Flow:** create/move/undelete docs → room check (readonlyDocs→402 payment-required FIRST, then standing, then count). Share deltas snapshot before/after member maps and enforce per-doc/per-role caps on the DELTA only. Assistant calls go through increaseUsage which creates-or-resets the Limit row inside one transaction and returns ApiError-as-value rethrown outside.
**Invariant:** Limit rows are LAZY artifacts: `-1` means unlimited ("not possible to do in stripe"), products without baseMaxAssistantCalls are "basically unlimited" and skip tracking entirely. Reset correctness leans on comparing expected-vs-recorded resetAt — clock-skewed servers converge because the check re-fires every read. Porters who enforce limits at API-layer instead of mutation-layer miss moveDoc's cross-org re-check.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "can enforce limits on number of workspaces" test/gen-server/lib/limits.ts'` → :82.
`bash -c 'grep -c "_checkRoomForAnotherDoc\|_restrictShares" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 6.
Direct tests: `test/gen-server/lib/limits.ts` (615L suite: workspaces :82 + doc/share/assistant families), readonly downgrade via `features.readOnlyDocs` in Authorizer suites.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"_checkRoomForAnotherDoc _restrictShares increaseUsage _getOrCreateLimitAndReset maxDocsPerOrg","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — structured limit errors + lazy counter resets compose into any SaaS quota layer.
