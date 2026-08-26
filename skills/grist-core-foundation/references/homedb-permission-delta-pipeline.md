<!-- capsule-v2 -->
# PermissionDelta pipeline — how does an email-keyed `{alice@x: "editor"}` delta become verified, self-change-guarded group mutations?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What is the exact validation ladder between a PATCH /access body and rows changing in `group_users`?

## verifyAndLookupDeltaEmails → _createNotFoundUsers → _updateUserPermissions; every stage has a fail-closed guard
**Path/Symbol:** `app/gen-server/lib/homedb/UsersManager.ts`: `verifyAndLookupDeltaEmails` (:733–828), `_mergeIndistinguishableEmails` (:1016–1032), `translateDeltaEmailsToUserIds` (:830–847); `HomeDBManager.ts`: `_createNotFoundUsers` (:3662–3677), `_updateUserPermissions` (:4253–4291), `_failIfPowerfulAndChangingSelf` (:4173–4184), `PermissionDeltaAnalysis` type (UsersManager import :24).
**Signature:** `verifyAndLookupDeltaEmails(userId, delta: PermissionDelta, isOrg = false, transaction?) => Promise<PermissionDeltaAnalysis>` where analysis = `{foundUserDelta, foundUsers, notFoundUserDelta, permissionThreshold, affectsSelf}`.
**Data Shape:** Input `{users?: {[email]: role|null}, maxInheritedRole?}`. Shape validity differs by resource: org REQUIRES inherit-or-users (`isOrg && (hasInherit || !hasUsers)` throws), doc/ws requires at least one of the two. Output splits emails into found-user ids vs not-found (invitable) emails.

### Decisive source
```ts
// This deals with the problem posed by receiving a PermissionDelta specifying a
// role for both alice@x and Alice@x. We do not distinguish between such emails.
// If there are multiple indistinguishabe emails, we preserve just one of them,
// assigning it the most powerful permission specified. The email variant perserved
// is the earliest alphabetically.
for (const displayEmail of Object.keys(delta.users).sort()) {
  const email = normalizeEmail(displayEmail);
  const role = delta.users[displayEmail];
  const key = displayEmails[email] = displayEmails[email] || displayEmail;
  users[key] = users[key] ? roles.getStrongestRole(users[key], role) : role;
}
```
Threshold + self-guard:
```ts
const removingSelf =
  userIdsAndEmails.length === 1 &&
  userIdsAndEmails[0] === String(userId) &&
  delta.maxInheritedRole === undefined &&
  foundUserIdDelta[userId] === null;
const permissionThreshold = removingSelf ? Permissions.VIEW : Permissions.ACL_EDIT;
```

**Flow:** merge dupes → validate maxInheritedRole against basic names → validate roles (`members` only legal on org) → bulk-lookup existing users → everyone@+org+non-null-role+non-support → 403 spam guard → invalid-email tolerated ONLY for removals (legacy cleanup) → `_updateUserPermissions` re-buckets ALL members into top-level groups by rewritten delta (mutates groups in place; callers snapshot `membersBefore` FIRST) → save groups → `scrubUserFromOrg` for org removals.
**Invariant:** The threshold trick lets a lone user drop THEMSELVES with mere VIEW rights while any other change needs ACL_EDIT. `_updateUserPermissions` folds unaffected users into `userDelta` as a side effect ("so that we have a record of where they are") — callers relying on delta purity double-count. A porter applying deltas per-email instead of merged-by-normalized-email silently downgrades `Alice@x` when `alice@x` also appears.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -c "getStrongestRole" app/gen-server/lib/homedb/UsersManager.ts'` → ≥ 1.
`bash -c 'grep -n "Include a maxInheritedRole value and check that the operation fails with 400" test/gen-server/ApiServerAccess.ts'` → :365.
Direct tests: `test/gen-server/ApiServerAccess.ts` (maxInheritedRole set/removed ladder :587–620), `test/gen-server/lib/scrubUserFromOrg.ts` ("cannot remove users from orgs without permission" :336).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"verifyAndLookupDeltaEmails PermissionDelta _updateUserPermissions translateDeltaEmailsToUserIds","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — this is the write-side contract of home-DB sharing; every SaaS sharing feature ports this ladder or inherits its bugs.
