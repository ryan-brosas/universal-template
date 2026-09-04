<!-- capsule-v2 -->
# Query-result normalization funnel — how do you convert raw permission bits, personal-org domains and login rows into API-safe shapes in ONE recursive pass?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where do numeric `permissions` become role names, where are personal-org domains synthesized, and which entities get silently dropped?

## `_normalizeQueryResults` walks the entity tree converting `permissions`→`access`, rewriting `domain`, collapsing logins/managers/prefs, then `_isForbidden` filters
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `_normalizeQueryResults` (:4753–4856), `_isForbidden` (:4860–4874), array filter inside it (:4762–4770), domain rewrite (:4789–4792), `getRoleFromPermissions` (`GroupsManager.ts` :256–258).
**Signature:** `_normalizeQueryResults(value: any, options: { suppressDomain?, scope?, parentPermissions? } = {}): any`; `_isForbidden(entity: any, ignoreAccess: boolean, scope?: Scope): boolean`.
**Data Shape:** scalar `permissions` → `access: roles.Role|null` + optional `public: true` (when `PUBLIC` bit set); JSON `permissions` (multi-user) → `accessOptions: {access, id, email, perms, name}[]`. `logins` array MUST have exactly one entry else `ApiError("Cannot find unique login for user", 500)`.

### Decisive source
```ts
if (key === "domain") {
  value[key] = this.normalizeOrgDomain(value.id, subValue, value.owner?.id,
    false, options.suppressDomain);
  continue;
}
...
if (typeof subValue === "number" || !subValue) {
  // Find the first special group for which the user has all permissions.
  value.access = this._groupsManager.getRoleFromPermissions(subValue || 0);
  if (subValue & Permissions.PUBLIC) { value.public = true; }
}
...
delete value.permissions;  // permissions is not specified in the api, so we drop it.
```
Filtering rule:
```ts
const ignoreAccess = options.parentPermissions &&
  (options.parentPermissions & Permissions.REMOVE) && items.length > 0 && !items[0].docs;
return items.filter(v => !this._isForbidden(v, Boolean(ignoreAccess), options.scope));
```

**Flow:** `_verifyAclPermissions` gets entities+raw → `_normalizeQueryResults(entities)` recurses; orgs without the `vanityDomain` feature force `suppressDomain: true` (domains render as `o-NNNN`); billingAccount managers collapse to boolean `isManager`; prefs arrays split into `orgPrefs/userOrgPrefs/userPrefs` by orgId/userId nullness; forbidden entries (access null / empty accessOptions / `filteredOut`) drop unless caller has REMOVE on parent and items aren't workspaces.
**Invariant:** Domain is NEVER stored for personal orgs — computed at read time via `normalizeOrgDomain` (:2908–2932: `docs-<prefix><ownerId>` vs merged `docs`/`docs-s` vs `o-<id>`); a porter who persists domains breaks vanity-domain suppression. Empty-list + marked-failure distinction lives in `_verifyAclPermissions` BEFORE normalization (404 vs 403), so normalization itself only ever drops CHILD entities.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -c "structuredClone" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 10 (same file's clone discipline).
`bash -c 'grep -n "does not show workspaces for docs user does not have access to" test/gen-server/lib/removedAt.ts'` → :442.
Direct tests: `test/gen-server/lib/listing.ts` :157 ("lists empty workspaces"), `test/gen-server/lib/mergedOrgs.ts` (:38 pooling, :97 doc under merged domain).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"_normalizeQueryResults _isForbidden normalizeOrgDomain accessOptions suppressDomain","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — pairs with the SQL gate as the read-side half of the authorization contract; distinct from `requestUtils.pruneAPIResult` (field denylist at send-time) — this layer reshapes/filters entities, that layer strips internal fields.
