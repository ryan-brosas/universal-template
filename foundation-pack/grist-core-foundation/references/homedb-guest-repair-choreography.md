<!-- capsule-v2 -->
# Guest-group repair choreography — why do workspace/org guest groups get recomputed after every membership change, and in what order?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does "share a doc with someone → they appear as org guest" stay true without triggers?

## Denormalized guest membership is REPAIRED (not incrementally updated) from first-level doc/ws users after every access mutation
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `_repairWorkspaceGuests` (:3954–3984), `_repairOrgGuests` (:3991–4016, NOTE: must run AFTER workspace repair), `filterEveryone` (`UsersManager.ts` :913–918), `setGroupUsers` (`GroupsManager.ts` :183–206).
**Signature:** `_repairWorkspaceGuests(scope, wsId, transaction?)`; `_repairOrgGuests(scope, orgKey, transaction?)`; `setGroupUsers(manager, groupId, usersBefore, usersAfter)`.
**Data Shape:** Repair inputs are entity graphs with `aclRules→group→memberUsers` populated; the recomputed set = first-level users of non-soft-deleted children, minus everyone@ UNLESS anon@ is also present (`filterEveryone`: "material shared with everyone@ doesn't become listable/discoverable by default").

### Decisive source
```ts
const wsWithDocsQuery = this._workspace(scope, wsId, { manager })
  .leftJoinAndSelect("workspaces.docs", "docs")
  .leftJoinAndSelect("docs.aclRules", "doc_acl_rules")
  .leftJoinAndSelect("doc_acl_rules.group", "doc_groups")
  .leftJoinAndSelect("doc_groups.memberUsers", "doc_users")
  .andWhere("docs.removed_at IS NULL")  // Don't grant guest access for soft-deleted docs.
  .andWhere("doc_users.id is not null");
const wsWithDocs = await wsWithDocsQuery.getOne();
await this._groupsManager.setGroupUsers(manager, wsGuestGroup.id, wsGuestGroup.memberUsers,
  this._usersManager.filterEveryone(
    UsersManager.getResourceUsers(wsWithDocs?.docs || []),
  ),
);
```
TypeORM workaround forcing explicit diff writes (`GroupsManager.setGroupUsers`):
```ts
// TypeORM's .save() method appears to be unreliable for a ManyToMany relation with a
// table with a multi-column primary key, so we make the update using explicit deletes and inserts.
.insert()
// ... we may get a duplicate key error if two documents are added at the same time
.orIgnore()
```

**Flow:** call sites: `addDocument` (:1798–1799 repairs ws then org), `deleteDocument` (:2023–2024), `updateDocPermissions` (:2369–2370), `updateWorkspacePermissions` (:2296), `deleteWorkspace`/`softDeleteWorkspace` (:1680/:3354 org-only), `moveDoc` (:2712–2721 BOTH sides of source and destination), `_doAddWorkspace` (:4052), `_setDocumentDeletionProperty` (:3889–3890). Ordering contract: ws-repair before org-repair because org guests derive FROM workspace guests.
**Invariant:** Repairs run INSIDE the same transaction as the mutation but tolerate concurrent unique-violations silently ("those functions... are ignoring any unique constraints errors" — addDocument comment :1795–1797). Soft-deleted docs/workspaces never contribute guests. A porter who updates only the directly-acted-on group leaves stale org-level access — the whole design bets on eventual-consistency-by-repair rather than perfect incremental bookkeeping.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -c "_repairOrgGuests(" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 10.
`bash -c 'grep -n "can remove users from orgs while preserving workspace access" test/gen-server/lib/scrubUserFromOrg.ts'` → :205.
Direct tests: `test/gen-server/lib/scrubUserFromOrg.ts` full suite (guest preservation after org removal); `test/gen-server/ApiServerAccess.ts` guest assertions.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"_repairWorkspaceGuests _repairOrgGuests setGroupUsers filterEveryone guest","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — denormalize-then-repair is the transferable pattern; the ordering + soft-delete filters are what a porter gets wrong.
