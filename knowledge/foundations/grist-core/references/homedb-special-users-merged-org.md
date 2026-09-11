<!-- capsule-v2 -->
# Special users & merged personal org — why do anonymous/previewer/everyone/support exist as DB rows, and how does one virtual org pool all personal sites?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How are the four synthetic identities materialized, and where does the `docs` pseudo-org get stitched?

## Boot-time special-user creation cached by email; merged org is domain-keyed (`docs`/`docs-s`, id 0) and rewritten at read time
**Path/Symbol:** `app/gen-server/lib/homedb/UsersManager.ts`: `_specialUserIds` cache (:93), getters (:135–166, throw when unavailable), `initializeSpecialIds` (:644–661), SUPPORT_EMAIL from appSettings (:42–45), NON_LOGIN_EMAILS (:48), `getExcludedUserIds` (:863–865). `HomeDBManager.ts`: `isMergedOrg`/`mergedOrgDomain` (:2950–2963), anon-org synthesis in getOrg (:637–661), `_mergePersonalOrgs` (:5123–5130), `_wherePlainOrg` docs-prefix routing (:4514–4531).
**Signature:** `getAnonymousUserId()/getPreviewerUserId()/getEveryoneUserId()/getSupportUserId()` — all throw if boot seeding hasn't run; `isMergedOrg(orgKey) => orgKey === mergedOrgDomain() || orgKey === 0`.
**Data Shape:** Merged org responses carry `id: 0` + `domain: "docs"`; anonymous gets a fully SYNTHETIC org object (ANONYMOUS_PLAN, individual billing account, `access: "viewers"`) never persisted. Personal orgs keep `domain: null` in the DB — presentation computes `docs-<ownerId>` or pooled `docs`.

### Decisive source
```ts
// The merged organization is a special pseudo-organization patched together from all
// the material a given user has access to...
public isMergedOrg(orgKey: string | number | null) {
  return orgKey === this.mergedOrgDomain() || orgKey === 0;
}
```
Query-side expansion of the pseudo-org:
```ts
private _wherePlainOrg<T extends WhereExpressionBuilder>(qb: T, org: string | number): T {
  ...
  if (org.startsWith(`docs-${this._idPrefix}`)) {
    // this is someone's personal org
    const ownerId = org.split(`docs-${this._idPrefix}`)[1];
    qb = qb.andWhere("orgs.owner_id = :ownerId", { ownerId });
```
And `_filterByOrgGroups` on merged orgs: `.andWhere("orgs.owner_id is not null")` — "Select from universe of personal orgs... filtering via joins against the user and groups the user belongs to".

**Flow:** every member-count/billing path subtracts `getExcludedUserIds()` (support+everyone+anonymous) so synthetic users never count as seats; listing for anonymous collapses to the current site's org or empty array (:969–982); `getBestUserForOrg` returns null for merged org ("parsing/mapping the results in TypeORM is slow").
**Invariant:** everyone@ vs anon@ have OPPOSITE listing semantics: shares with everyone@ make resources accessible-but-unlisted (contribution zeroed in `list` style), shares with anon@ make them listed. A porter who merges the two accounts breaks discoverability invariants pinned by test/gen-server/lib/everyone.ts.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "skips picking a user for merged personal org" test/gen-server/lib/HomeDBManager.ts'` → :295.
`bash -c 'grep -c "getSpecialUserId\|_specialUserIds" app/gen-server/lib/homedb/UsersManager.ts'` → ≥ 6.
Direct tests: `test/gen-server/lib/mergedOrgs.ts` (pooling :38, doc under merged domain :97), `test/gen-server/lib/everyone.ts` (4 share-listing its), `test/gen-server/lib/previewer.ts`, `HomeDBManager.ts` :223–275 pooling family.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"mergedOrg isMergedOrg ANONYMOUS_USER_EMAIL PREVIEWER_EMAIL EVERYONE_EMAIL support","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — synthetic-identity + virtual-org pooling is the load-bearing context behind half the branches in this file.
