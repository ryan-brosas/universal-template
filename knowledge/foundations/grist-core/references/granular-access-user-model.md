<!-- capsule-v2 -->
# Granular access user model — how is a session's effective user built, and how do user-attribute rules and "view as" overrides attach to it?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How does `getUser` assemble Access/ShareRef/UserID/Email plus arbitrary user-attribute rows, and how do ACL rules read `user.*`?

## getUser assembly + user-attribute rules + view-as override
**Path/Symbol:** `app/server/lib/GranularAccess.ts` — `getUser` (:351-451), `_getUserAttributes` (:2129-2133), `_getViewAsUser` (:2171+), `getNominalAccess` (:1381-1397), `inputs` (:462-468); the `User` shape in `app/common/User.ts`.
**Signature:** `getUser(docSession): Promise<User>`; `inputs(docSession): Promise<PredicateFormulaInput>` returns `{ user, docId, mask }`; `getNominalAccess(docSession): Promise<Role|null>`.
**Data Shape:** `User` = `{ Access, ShareRef, UserID, Email, Name, LinkKey, Origin, SessionID, IsLoggedIn, UserRef, [attribute: string]: any }`. `SessionID` = `a${altSessionId}` for anonymous, `u${UserID}` otherwise. User-attribute rules live in `_grist_ACLRules` with a `charId` (e.g. `Email`) used as the lookup key against the `User` object.

### Decisive source
```ts
// getUser — the enrichment loop over user-attribute rules
for (const clause of this._ruler.ruleCollection.getUserAttributeRules().values()) {
  if (clause.name in user) { log.warn(`User attribute ${clause.name} ignored; conflicts with an existing one`); continue; }
  if (attrs.rows[clause.name]) { user[clause.name] = attrs.rows[clause.name]; continue; }
  let rec = new EmptyRecordView();
  try {
    const noCase = clause.charId === "Email" ? ` COLLATE NOCASE` : "";
    const rows = await this._fetchQueryFromDB({ tableId: clause.tableId, filters: {},
      where: { clause: `${quoteIdent(clause.lookupColId)}${noCase} = ?`, params: [get(user, clause.charId)] } });
    if (rows && rows[2].length > 0) { rec = new RecordView(rows, 0); }
    user[clause.name] = rec; attrs.rows[clause.name] = rec;   // cached per session
  } catch (e) { log.warn(`User attribute ${clause.name} failed`, e); }
}
```
```ts
// view-as override — only owners may impersonate
if (linkParameters.aclAsUserId || linkParameters.aclAsUser) {
  if (access !== "owners") { throw new ErrorWithCode("ACL_DENY", "only an owner can override user"); }
  const override = attrs.override || (attrs.override = await this._getViewAsUser(linkParameters));
  access = override.access; fullUser = override.user;
}
```

**Flow:** `getUser` starts from `getDocSessionAccess` (the coarse role) and `getDocSessionShare` (resolves the `_grist_Shares` rowId → `ShareRef`); `forkingAsOwner` bluffs access to `owners` (the session is only ever used to read a fork); `aclAsUser`/`aclAsUserId` (owner-only) swaps in an override; a share link anonymizes `fullUser`; then every user-attribute rule looks up a row in its table keyed on the user's own field and attaches it as `user.<name>` (cached per session in `_userAttributesMap`). `inputs` hands `{user, docId, mask}` to every rule predicate, so `user.Access`, `user.Email`, and any `user.<attribute>` are available in ACL formulas.
**Invariant:** user-attribute rules are evaluated lazily and CACHED per docSession (WeakMap); `getUser` must be called before rules evaluate (the `_checkUserAttributes` reload detector compares cached rows across bundles and throws `NEED_RELOAD` when a previously-seen attribute value changes). The Email lookup is `COLLATE NOCASE` (case-insensitive); other charIds are exact. A name collision with a built-in `User` field is silently ignored (warn + skip) — a porter must not let rules shadow `Access`/`Email` etc.
**Probe:** `test/server/lib/GranularAccess.ts` — "forces a row check for rules with memo and rec" (:239) and the `user.Access == OWNER` predicates throughout pin the user object; the `aclAsUser`/`aclAsUserId` owner-only gate is exercised by the "view as" suites.
**Coverage caveat:** the `_checkUserAttributes` NEED_RELOAD path has no dedicated unit test (pinned indirectly); the NOCASE Email lookup is source-verified only.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "GranularAccess getUser userAttributes getNominalAccess inputs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the session→User assembly (Access/ShareRef/UserID + attribute-row enrichment with per-session caching and NOCASE email lookup) for any rule-engine that needs `user.*` in predicates; adapt the attribute-rule storage; omit the share-link anonymization and view-as override if your product has no shares/impersonation.
