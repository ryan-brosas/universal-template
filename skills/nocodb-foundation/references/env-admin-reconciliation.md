<!-- capsule-v2 -->
# Env-admin upsert state machine — what exactly happens when NC_ADMIN_EMAIL/PASSWORD collide with existing users, and which accesses migrate?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When the env admin email changes, how do the old account's base memberships move to the super admin without privilege loss?

## Four-branch reconciliation under one transaction
**Path/Symbol:** `packages/nocodb/src/helpers/initAdminFromEnv.ts:initAdminFromEnv` (whole 295L); called from `init-meta-service.provider.ts:131` before EE-load and upgrader.
**Signature:** `initAdminFromEnv(_ncMeta = Noco.ncMeta): Promise<void>`; rolesLevel ladder {owner:0, creator:1, editor:2, commenter:3, viewer:4}; roles granted 'org-level-creator,super'.
**Data Shape:** inputs NC_ADMIN_EMAIL (sanitized+lowercased) / NC_ADMIN_PASSWORD (SDK validatePassword with hint); every write path rotates token_version via randomTokenString().

### Decisive source
```ts
// if admin user already have access to the base
// then update role based on the highest access level
if (userProject) {
  if (rolesLevel[userProject.roles] > rolesLevel[existingUserProject.roles]) {
    await BaseUser.update({...}, userProject.base_id, user.id, existingUserProject.roles, ncMeta);
  }
} else {
  // if super doesn't have access then add the access
  await BaseUser.insert({ ...existingUserProject, fk_user_id: user.id }, ncMeta);
}
// delete the old base access entry from DB
await BaseUser.delete(existingUserProject.base_id, existingUserProject.fk_user_id, ncMeta);
```
(:137–:170)

**Flow:** env pair present → validate email/password (boxen-banner + process.exit(1) on invalid) → open transaction. Branch 1 FIRST USER EVER: insert super admin + verifyDefaultWorkspace. Otherwise iterate existing super users; for each, Branch 2 email DIFFERS from a super user: if another account already holds the new email — migrate that account's project_users onto the admin one-by-one keeping the HIGHER role (lower rolesLevel number wins), delete each old row, then DELETE the old user entirely and rewrite the super admin's credentials; else just rewrite credentials. Branch 3 email SAME as super user: re-hash with the stored salt and only rotate password/token when they differ. Branch 4 NO super user exists at all: upgrade-or-create the target account with super roles. Finally verifyDefaultWsOwner + commit.
**Invariant:** role migration must compare by the numeric LADDER, not string equality, and never downgrade an existing higher access. The old account's deletion comes AFTER its memberships moved — inside one transaction so a mid-migration failure rolls back cleanly. Cache keys for BOTH old user id AND email are invalidated explicitly. Every credential write refreshes token_version, killing outstanding refresh tokens.
**Probe:** `cd packages/nocodb && grep -c "rolesLevel" src/helpers/initAdminFromEnv.ts` (=3: decl + both comparison operands) and `grep -c "randomTokenString" src/helpers/initAdminFromEnv.ts` (=7 incl imports/uses) and `grep -cE "verifyDefaultWorkspace|verifyDefaultWsOwner" src/helpers/initAdminFromEnv.ts` (=5).
**Direct test:** none upstream for initAdminFromEnv.ts — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "initAdminFromEnv rolesLevel verifyDefaultWorkspace superUsers", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt transactional four-branch reconciliation + ladder-based role merge + token_version rotation; adapt role names/ladder to your RBAC; omit if you provision admins exclusively through UI. Coverage caveat: grep-pinned only.
