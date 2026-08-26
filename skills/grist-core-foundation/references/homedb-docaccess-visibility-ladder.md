<!-- capsule-v2 -->
# getDocAccess visibility ladder — who may see whom on a document, decided in four nested branches?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does the ACL UI decide whether to list all collaborators, only viewers, or just yourself?

## Editor-at-doc → org-owner sees all; ws-owner sees ws+doc viewers; plain editor sees doc viewers; below editor sees only self — with flatten/fork post-processing
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `getDocAccess` (:2496–2630), branch ladder (:2561–2599), role-map assembly (:2525–2536), `_filterAccessData` (:5396–5419), flatten+fork fixups (:2605–2620).
**Signature:** `getDocAccess(scope: DocScope, options?: {flatten?: boolean, excludeUsersWithoutAccess?: boolean}) => Promise<QueryResult<PermissionData>>`.
**Data Shape:** Five role maps feed the decision: `docMap` (common groups incl guests), `wsMap`/`wsMapWithMembership`, `orgMap` (basic = inheritable), `orgMapWithMembership`; per-user output `{access: docMap|null, parentAccess: effective(max(wsMap, inheritFromOrg)), isMember}` where `inheritFromOrg = getWeakestRole(orgMap[u.id], wsMaxInheritedRole)`.

### Decisive source
```ts
// - If user is at least editor on the document (but not a public editor), then we return all users
//   who can see the document.
// - If such user is also an owner of a parent resource (workspace or org), then we include all
//   users on that resource, including guest users.
const isPublic = !thisUser || thisUser.anonymous || !docRealAccess;
if (!isPublic && roles.canEdit(docRealAccess)) {
  if (roles.canEditAccess(orgMap[scope.userId] ?? null)) {
    // If this user is an org owner, return all users unfiltered.
  } else if (roles.canEditAccess(thisUser?.parentAccess ?? null)) {
    // If user is owner of the workspace, return all users on the workspace and on the document.
    users = users.filter(user => canViewDoc(user) || canViewWorkspace(user));
  } else {
    users = users.filter(user => canViewDoc(user));
  }
  // If user can't change access on the document, instruct UI to just show user's role.
  if (!roles.canEditAccess(getRealAccess(thisUser, { maxInheritedRole }) ?? null)) {
    personalMetadata.public = false; personalMetadata.personal = true;
  }
} else {
  users = thisUser ? [thisUser] : [];
  personalMetadata.public = isPublic; personalMetadata.personal = true;
}
```

**Flow:** fork/new-doc shortcuts (unsaved docs echo the caller as owner :2505–2520) → trunk lookup at VIEW → map assembly → ladder → optional `excludeUsersWithoutAccess` → flatten mode collapses parentAccess and nulls maxInheritedRole (forks ALWAYS flatten) → per-user `_setForkAccess`. Org/ws-level access endpoints reuse `_filterAccessData`: non-owners get `users.length = 0` + only themselves + `{personal:true, public:!realAccess}`.
**Invariant:** The previewer bypasses ALL filtering (:2569). `canEditAccess` (ACL_EDIT permission) is the discriminator between owner-tiers — NOT role names. A porter who filters by role string breaks tutorials/public editors where realAccess ≠ stored access.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "excludeUsersWithoutAccess" app/gen-server/lib/homedb/HomeDBManager.ts | head -2'` → :2498 signature + :2601 filter.
`bash -c 'grep -rn "flatten" test/gen-server/ApiServerAccess.ts | head -3'` → ≥ 2 assertions.
Direct tests: `test/gen-server/ApiServerAccess.ts` access-listing its (owner/editor/viewer visibility matrices); `HomeDBCaches.ts` exercises the flattened previewer fetch.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"getDocAccess _filterAccessData getRealAccess parentAccess excludeUsersWithoutAccess","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — collaborator-visibility policy is a distinct contract from permission enforcement; both must port together for ACL UIs.
