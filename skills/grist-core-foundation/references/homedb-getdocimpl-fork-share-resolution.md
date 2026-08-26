<!-- capsule-v2 -->
# getDocImpl fork/share/new-doc resolution — how does one doc-lookup entry point serve trunks, forks, share keys and untitled new docs?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where do `~user` forks, `new~` docs and share-key links resolve WITHOUT a database row of their own?

## `getDocImpl` parses the urlId grammar then branches: Share table → NEW_DOCUMENT_CODE synthetic → trunk lookup with fork fixups
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `getDocImpl` (:999–1134), wrapper `getDoc` (:1138–1151, removed-filter), `_setForkAccess` (:4141–4165), `_fork` query builder (:4396–4427). Grammar source: `parseUrlId` (`app/common/gristUrls.ts`).
**Signature:** `getDocImpl(key: DocAuthKey, transaction?) => Promise<Document>`; branch keys: `shareKey`, `urlId === NEW_DOCUMENT_CODE`, else trunk.
**Data Shape:** Synthetic share doc is a plain object cast `as any` — `{name, id: res.docId, access: "editors", workspace, aliases: [], ...}` with comment "a share may have view/edit access, need to check at granular level". Fork fixup rewrites identity fields: `doc.trunkId = doc.id; doc.id = buildUrlId({trunkId, forkId, forkUserId, snapshotId})`; `doc.trunkAccess = doc.access`.

### Decisive source
```ts
if (urlId === NEW_DOCUMENT_CODE) {
  if (!forkId) { throw new ApiError("invalid document identifier", 400); }
  // We imagine current user owning trunk if there is no embedded userId, or
  // the embedded userId matches the current user.
  const access = (forkUserId === undefined || forkUserId === userId) ? "owners" :
    (userId === this._usersManager.getPreviewerUserId() ? "viewers" : null);
  if (!access) { throw new ApiError("access denied", 403); }
```
Fork-access ladder (`_setForkAccess`, tutorial vs normal):
```ts
//   - If there is no ~USERID in fork id, then all viewers of trunk are owners of the fork.
//   - If there is a ~USERID in fork id, that user is owner, all others are at most viewers.
if (ids.forkUserId === undefined && roles.canView(res.access)) { res.access = "owners"; }
if (ids.forkUserId !== undefined) {
  if (ids.userId === ids.forkUserId) {
    if (roles.canView(res.access)) { res.access = "owners"; }
  } else {
    // reduce to viewer if not already viewer
    res.access = roles.getWeakestRole("viewers", res.access);
  }
}
```

**Flow:** websocket/HTTP doc opens → `getDoc` → cache fill + removed-filter → `getDocImpl`: shareKey path returns editors-access synthetic (granular checks deferred to GranularAccess); new-doc path builds a fake doc inside the SUPPORT user's example workspace with anonymous free-plan features patched onto billingAccount; normal path runs the CTE doc query (`_doc` with `showAll:true`) — ambiguity guarded post-query (`docs.length > 1 → "ambiguous document request"` 400) because caching needs the raw row. Read-only downgrade: `features.readOnlyDocs || this.isReadonly() || !inGoodStanding` caps access at viewers (:1104–1110).
**Invariant:** Disabled-user check piggybacks on the SAME query via unconditional join `leftJoin(User, "users", "users.id = :userId")` selecting `users.disabled_at` — deliberately localized here because only websocket traffic hits it (:1082–1092). A porter who moves that check into every home-DB method pays an extra round trip per call; one who drops it lets disabled users keep live websockets.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -c "NEW_DOCUMENT_CODE" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 3.
`bash -c 'grep -n "can fork docs" test/gen-server/lib/HomeDBManager.ts'` → :423.
Direct tests: `test/server/lib/Authorizer.ts` :286 ("viewer can fork doc" asserting parsed `forkUserId`) and :300 ("anon can fork doc"); `test/gen-server/lib/HomeDBManager.ts` :423 fork family incl. `_addForks` shape assertions.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"getDocImpl parseUrlId NEW_DOCUMENT_CODE _setForkAccess _addForks shareKey","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — the urlId-grammar-to-entity resolution is the single weirdest contract in the home DB; porters who model forks as rows break tutorials/unsaved docs.
