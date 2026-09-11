<!-- capsule-v2 -->
# getOrgs listing semantics — how does the org list balance personal-first ordering, anonymous collapse, and everyone@ non-discoverability?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What exact ORDERING and FILTERING contract does the workspaces landing page depend on?

## Personal org pinned first via conditional SQL order; anonymous users get at most the current site; membership filter accepts email-profile lists via cross join
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `getOrgs` (:948–984), personal-first orderBy (:956–961), anonymous collapse (:969–982), `_filterByOrgGroups` (:4554–4588), `getMergedOrgs` (:987–993) + `_mergePersonalOrgs` (:5123–5130), `getOrgWorkspaces` support-org-last ordering (:3876–3884).
**Signature:** `getOrgs(scope, options?: {ignoreEveryoneShares?: boolean})`; single-user path adds `.orderBy("(coalesce(users.id,0) = :userId)", "DESC")`.
**Data Shape:** Multi-user (session profiles) path joins a derived `profiles` table (`users ⋈ logins where logins.email in (...)`) with `"1 = 1"` cross-join ON — "the shortest portable way to do a cross join in postgres and sqlite via typeorm"; empty email set → dummy user row with casts ("for a postgres 9.5 issue where type inference fails").

### Decisive source
```ts
if (UsersManager.isSingleUser(users)) {
  // When querying with a single user in mind, we keep our api promise
  // of returning their personal org first in the list.
  queryBuilder = queryBuilder
    .orderBy("(coalesce(users.id,0) = :userId)", "DESC")
    .setParameter("userId", users);
}
...
// The anonymous user is a special case. It may have access to potentially many orgs,
// but listing them all would be kind of a misfeature... We compromise, and report at
// most the org of the site the user is on (or nothing ...).
if (this._usersManager.isAnonymousUser(users) && !listPublicSites) {
  if (domain && !this.isMergedOrg(domain)) {
    queryBuilder = this._whereOrg(queryBuilder, domain);
  } else {
    return { status: 200, data: [] };
  }
}
```

**Flow:** `_withAccess` marks permissions per resource → `_filterByOrgGroups` narrows to direct membership OR everyone@ (single-user) / email match (profiles); previewer bypasses the filter entirely (:4562–4564). Workspaces listing additionally orders support-org samples LAST (`coalesce(orgs.owner_id = :supportId, false)`).
**Invariant:** The personal-first promise is API-level (comment: "we keep our api promise") — clients rely on it. ignoreEveryoneShares mode exists for endpoints that must not count everyone@ shares as membership. Merged-org mode rewrites id→0/domain→docs AFTER fetch so persistence never stores the pseudo values.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "1 = 1" app/gen-server/lib/homedb/HomeDBManager.ts'` → :5032 area.
`bash -c 'grep -n "it(" test/gen-server/lib/listing.ts | head -4'` → suite entry points.
Direct tests: `test/gen-server/lib/listing.ts` (196L), `mergedOrgs.ts` pooling its, `HomeDBManager.ts` :223–295 pool + best-user families.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"getOrgs _mergePersonalOrgs _filterByOrgProfiles _filterByOrgGroups orderBy","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — listing contracts (order promises + discoverability rules) are what client code silently depends on and ports worst.
