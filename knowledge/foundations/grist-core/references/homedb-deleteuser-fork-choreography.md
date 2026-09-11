<!-- capsule-v2 -->
# deleteUser fork-orphan choreography — why fork cleanup runs OUTSIDE the user-deletion transaction, and what the 503 bail means

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How do you delete a user whose forks are addressed by a composite key containing their id?

## Forks (external storage keyed by trunkId+forkId+forkUserId) are hard-deleted BEFORE the tx; a re-appearing fork inside the tx aborts with 503 retry-me
**Path/Symbol:** `app/gen-server/lib/homedb/UsersManager.ts`: `deleteUser` (:565–642), fork pre-scan (:584–600), in-tx re-check (:615–624), `buildUrlId` usage (:598); self-only guard (:567–570).
**Signature:** `deleteUser(scope: Scope, userIdToDelete: number, name?: string): Promise<QueryResult<User>>` — `scope.userId !== userIdToDelete` → 403 "not permitted to delete this user".
**Data Shape:** Fork identity = `{trunkId: doc.trunkId!, forkId: doc.id, forkUserId: doc.createdBy!}` composed via `buildUrlId`; storage deletion goes through `this._homeDb.storageCoordinator.hardDeleteDoc(fullId)` (absent coordinator → "no mechanism available to delete forks" hard error).

### Decisive source
```ts
// Deleting a user leaves their forks orphaned, inaccessible. Worse, even Grist loses
// track of how to access them on disk and in external storage, since they are identified
// using a composite key that includes the user id. So we delete the forks now.
// Deleting can be a relatively slow operation... So we do it outside the main transaction...
const forksToDelete = await this._connection.getRepository(Document).find({
  where: { createdBy: userIdToDelete, trunkId: Not(IsNull()) } });
for (const doc of forksToDelete) {
  ...
  await this._homeDb.storageCoordinator.hardDeleteDoc(fullId);
}
```
In-transaction tripwire:
```ts
docs.forEach((doc) => {
  if (doc.trunkId) {
    // We tried cleaning up forks before starting the transaction but one snuck back in? Just bail.
    throw new ApiError("Untimely document addition? Please retry.", 503);
  } else {
    doc.createdBy = null;
  }
});
```

**Flow:** outside tx — find+hard-delete all forks; inside tx — load user (logins+personalOrg+prefs), optional name cross-check (`user name did not match` 400), deleteOrg(personalOrg), null-out `createdBy` on surviving docs (FK constraint), raw-SQL delete from `group_users` ("We don't have a GroupUser entity, and adding one tickles lots of TypeOrm quirkiness"), remove logins, delete user row, return 200 + deleted entity.
**Invariant:** The 503 is deliberate retryable-failure semantics for a race the design cannot lock away (single-process Grist combines home server and doc worker — staying outside the tx avoids deadlock). A porter who moves fork deletion inside the transaction turns slow S3/doc-worker round trips into long row locks; one who skips it strands unreachable bytes forever.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "Untimely document addition" app/gen-server/lib/homedb/UsersManager.ts'` → :620.
`bash -c 'grep -rn "deleteUser" test/gen-server/ApiServer.ts | head -3'` → ≥ 2 hits (user self-delete coverage).
Direct tests: `test/gen-server/ApiServer.ts` user-management its (delete flows through /api /deleteUser path).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"deleteUser hardDeleteDoc trunkId forkUserId buildUrlId orphan","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — textbook out-of-tx side-effect choreography with an explicit in-tx consistency tripwire.
