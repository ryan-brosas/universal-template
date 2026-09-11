<!-- capsule-v2 -->
# addOrg billing-account selection ladder — which plan/billing account does a new org get, and what happens on domain collision?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does org creation decide between personal product, team product, teamInitial stub and a shared personal billing account?

## useNewPlan always branches a fresh BillingAccount with a 4-way product ladder; unique-constraint errors convert to "Domain already in use"; Home workspace + post-commit notification ride the same tx boundary
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `addOrg` (:1247–1401), product ladder (:1281–1293), billing allowlist (:1314–1331), save-catch (:1379–1387), `_doAddWorkspace({name:"Home"})` (:1390), notifications array + post-commit loop (:1258, :1392–1400).
**Signature:** `addOrg(user, props: Partial<OrganizationProperties>, options: {setUserAsOwner, useNewPlan, product?, billing?}, transaction?) => Promise<QueryResult<Organization>>`.
**Data Shape:** Product pick order (personal sites): `productNames.personal` when setUserAsOwner; else explicit `options.product`; else TEAM product if user IS support user ("called during creation of support@ user, before getSupportUserId() is available" — fragile by their own comment); else `teamInitial` STUB plan. BillingOptions writes pass an ALLOWLIST (`stripeCustomerId...paymentLink`) — unknown keys silently deleted.

### Decisive source
```ts
} catch (e) {
  if (e.name === "QueryFailedError" && e.message?.match(/unique constraint/i)) {
    throw new ApiError("Domain already in use", 400);
  }
  throw e;
}
...
// Add a starter workspace to the org. Any limits on org workspace
// count are not checked, this will succeed unconditionally.
await this._doAddWorkspace({ org: savedOrg, props: { name: "Home" } }, manager);

if (!options.setUserAsOwner) {
  // This user just made a team site (once this transaction is applied). Emit a notification.
  notifications.push(this._teamCreatorNotification(user.id));
}
```

**Flow:** validate name/domain (`checkSubdomainValidity` → 400 "Domain is not permitted") → billing branch (useNewPlan creates account+manager rows; else REUSE the user's personal-org account, externalId conflict → 400) → build org + five special groups (creator into owners :1366–1368) → mass-save [org, aclRules, groups, billingEntities] → starter "Home" workspace unconditionally → queue team-creator notification for non-personal sites → run notifications AFTER commit.
**Invariant:** The shared-account path logs `log.warn("Creating org with shared billing account")` — legacy mode kept only for tests/migrations. Domain uniqueness is enforced by DB constraint NOT pre-check (isDomainAvailable exists separately for availability UI), so the catch-translation is the real gate. A porter who pre-checks then inserts still needs the catch: two racers both pass the check.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "cannot duplicate a domain\|creates default plan if defined" test/gen-server/lib/HomeDBManager.ts'` → :138 / :105.
`bash -c 'grep -n "checkSubdomainValidity" app/gen-server/lib/homedb/HomeDBManager.ts | head -2'` → addOrg + updateOrg call sites.
Direct tests: `test/gen-server/lib/HomeDBManager.ts` :95 ("can add an org"), :105 (default plan), :138 (dup domain), :149 ("dodgy domain" blacklist).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"addOrg BillingAccount useNewPlan PERSONAL_FREE_PLAN checkSubdomainValidity","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — org-provisioning with plan ladder + constraint-as-gate is directly portable to multi-tenant SaaS.
