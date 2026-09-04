<!-- capsule-v2 -->
# SQL permission-marking subqueries — how do you authorize inside the query itself so forbidden rows and 403s never reach application code?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where is the single mechanism that turns group membership into a boolean every home-DB read is gated on?

## `_markIsPermitted` emits an `is_permitted`/`permissions` select over a 4-deep unrolled group-membership join
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `_markIsPermitted` (:4883–4972), `_getUsersAcls` (:4979–5045), `_joinToAllGroupUsers` (:5070–5080, public "for limited use by extensions"), verifier `_verifyAclPermissions` (:4668–4728) + module-level `verifyEntity` (:5475–5509).
**Signature:** `_markIsPermitted(resType: "orgs"|"workspaces"|"docs", users: AvailableUsers, accessStyle: AccessStyle, permissions: Permissions|null = VIEW, variableNamePrefix?)` — returns a qb-transform callback; callers `.addSelect(this._markIsPermitted(...), "is_permitted")`.
**Data Shape:** `accessStyle`: `"open"` (default; everyone@ grants access), `"list"` (listing: everyone@ shares contribute PUBLIC flag only, NOT access), `"openNoPublic"` (doc-prefs path). Membership join unrolls exactly 4 levels: `gu0` = direct member of the rule's group, `gu1..gu3` = via nested `group_groups` — comment: "enough nesting to support docs in workspaces in orgs, with one level of nesting held for future use".

### Decisive source
```ts
const userIdCols = ["gu0.user_id", "gu1.user_id", "gu2.user_id", "gu3.user_id"];
const publicFlagSql = `case when ` +
  hasAtLeastOneOfTheseIds(this._dbType, [everyoneId, anonId], userIdCols) +
  ` then ${Permissions.PUBLIC} else 0 end`;
// When listing, everyone@ shares do not contribute to access permissions,
// only to the public flag.
const contributionSql = accessStyle !== "list" ? "acl_rules.permissions" :
  `case when ` + hasOnlyTheseIdsOrNull(this._dbType, [everyoneId], userIdCols) +
  ` then 0 else acl_rules.permissions end`;
const previewerSql = `case when coalesce(${userIdCols.join(",")}) is null` +
  ` then acl_rules.permissions else 0 end`;
q = q.select(bitOr(this._dbType, `(${publicFlagSql} | ${contributionSql} | ${previewerSql})`, 8), "permissions");
```
Enforcement side (`_verifyAclPermissions`):
```ts
if (options.markedPermissions) {
  if (!results.raw.every(entry => entry.is_permitted)) {
    return { status: 403, errMessage: "access denied" };
  }
}
```

**Flow:** builder (`_org`/`_workspace`/`_doc`) marks → caller runs `_verifyAclPermissions` (list semantics: empty→404 unless `emptyAllowed`, marked-fail→403, then `_normalizeQueryResults` filters per-entity) or `verifyEntity` (single-entity: 0→404, >1→400 ambiguous, `is_permitted` falsy→403).
**Invariant:** The special previewer user bypasses via `acl_rules.permissions = :VIEW` OR-clause; anonymous listing rides a separate anon@ OR-clause ONLY in `list` style. `permissions !== null` asks a yes/no question (`& :permissions = :permissions ... limit 1`); `null` computes the full aggregate for display. A porter who collapses `list` vs `open` makes every everyone@-shared doc listed — a discoverability/security regression the tests pin.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -c "gu3" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 5.
`bash -c 'grep -n "editors and owners can list docs they cannot view" test/gen-server/lib/listing.ts'` → :98.
Direct tests: `test/gen-server/lib/listing.ts` ("editors and owners CANNOT list workspaces they cannot view" :134 — pins open-vs-list asymmetry), `test/server/lib/Authorizer.ts`.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"_markIsPermitted _getUsersAcls _joinToAllGroupUsers _verifyAclPermissions verifyEntity","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — this SQL-side gate plus result-normalization funnel is THE reusable contract of the home DB; everything else composes around it.
