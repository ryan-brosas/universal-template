<!-- capsule-v2 -->
# Org prefs three-flavor upsert — how do site-wide, user-on-site, and user-default preferences coexist in one table?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does one `prefs` table encode orgPrefs / userOrgPrefs / userPrefs, and which permission tier may write each?

## (org_id nullable, user_id nullable) matrix with COALESCE conflict targets; flavor choice drives permission ladder VIEW vs SCHEMA_EDIT
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `updateOrg` permission pre-ladder (:1425–1442) + pref upsert (:1477–1493), getOrg prefs join+ordering (:684–692), `_normalizeQueryResults` prefs split (:4822–4835).
**Signature:** props keys → `{orgPrefs: SCHEMA_EDIT + modifyOrg-ish path, userOrgPrefs/userPrefs: VIEW-only, anything else: SCHEMA_EDIT}`; upsert `.onConflict("(COALESCE(org_id,0), COALESCE(user_id,0)) DO UPDATE SET prefs = :prefs")`.
**Data Shape:** Flavor→row mapping: orgPrefs = {orgId, userId:null}; userOrgPrefs = {orgId, userId}; userPrefs = {orgId:null, userId}. Prefs values REPLACE wholesale ("Prefs are replaced in their entirety, not merged" — docstring :1410–1412).

### Decisive source
```ts
// That includes preference information specific to the site and the user,
// or specific just to the site, or specific just to the user.
qb = qb.leftJoinAndMapMany("orgs.prefs", Pref, "prefs",
  "(prefs.org_id = orgs.id or prefs.org_id IS NULL) AND " +
  "(prefs.user_id = :userId or prefs.user_id IS NULL)",
  { userId });
// Apply a particular order (user+org first if present, then org, then user).
// Slightly round-about syntax because Sqlite and Postgres disagree about NULL ordering...
qb = qb.addOrderBy("coalesce(prefs.org_id, 0)", "DESC");
qb = qb.addOrderBy("coalesce(prefs.user_id, 0)", "DESC");
```
```ts
const orgId = ["orgPrefs", "userOrgPrefs"].includes(flavor) ? org.id : null;
const userId = ["userOrgPrefs", "userPrefs"].includes(flavor) ? scope.userId : null;
await manager.createQueryBuilder().insert()
  .onConflict("(COALESCE(org_id,0), COALESCE(user_id,0)) DO UPDATE SET prefs = :prefs")
  .setParameters({ prefs: JSON.stringify(prefs) })  // TypeORM muddles JSON handling a bit here
```

**Flow:** read side joins ALL applicable rows for the user and normalizes them into named fields by nullness; precedence (user+org > org > user) comes from the ORDER BY trick consumed downstream. Write side loops the three flavors present in props and upserts each.
**Invariant:** Permission asymmetry is deliberate — a VIEWER may set their OWN prefs on a site they can't edit; org-wide changes need SCHEMA_EDIT. The JSON.stringify parameter workaround exists because TypeORM mangles json params in onConflict clauses. NULL-ordering divergence between sqlite/postgres is why COALESCE appears in BOTH the join order and the conflict target.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "userOrgPrefs" app/gen-server/lib/homedb/HomeDBManager.ts | head -3'` → :1435/:1481/:4827.
`bash -c 'grep -n "it(" test/gen-server/lib/prefs.ts | head -6'` → suite coverage.
Direct tests: `test/gen-server/lib/prefs.ts` (133L) + ApiServerAccess pref asserts.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"updateOrg userOrgPrefs Pref onConflict leftJoinAndMapMany","limit":8,"detail":"ids"}'`

**Verdict:** ADAPT — pairs with homedb-docprefs-dual-plane as the org-level twin; together they cover Grist's whole prefs plane.
