<!-- capsule-v2 -->
# DocAuth cache trio — where do doc access decisions get cached, and what must be flushed when?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How do three independent cache layers (request-scoped, process LRU, cross-server pubsub) stay coherent across permission mutations?

## Promise-keyed TTL map + PubSubCache pair; invalidation is deferred to post-commit callbacks so other servers only see committed truth
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `_docAuthCache = new MapWithTTL<string, Promise<DocAuthResult>>(DOC_AUTH_CACHE_TTL)` (:307), `getDoc` (:1138–1151), `getDocAuthCached` (:1167–1170), `flushSingleDocAuthCache` (:1187–1198), `setReadonly` flush (:359–364). `app/gen-server/lib/homedb/Caches.ts`: `HomeDBCaches` (:17–67, `DocAccessCacheTTL/DocPrefsCacheTTL = 5*60_000`, test hook `Deps`).
**Signature:** `getDocAuthCached(key: DocAuthKey): Promise<DocAuthResult>` via `mapGetOrSet(this._docAuthCache, stringifyDocAuthKey(key), () => makeDocAuthResult(this.getDocImpl(key)))`; `flushSingleDocAuthCache(scope: DocScope, docId: string)`.
**Data Shape:** Cache key = `stringifyDocAuthKey(key)` (`urlId userId org?`); alias-prefix matching on flush: `names.add(stringifyUrlIdOrg(docId, scope.org))` + every `Alias.urlId`, then delete keys whose first space-delimited token is in the set. `makeDocAuthResult` (:5524–5533) converts thrown errors into a RESULT `{docId:null, access:null, ..., error}` — errors are cached, not propagated.

### Decisive source
```ts
const aliases = await this._connection.manager.find(Alias, { where: { docId } });
// Construct a set of possible prefixes for cache keys.
const names = new Set(aliases.map(a => stringifyUrlIdOrg(a.urlId, scope.org)));
names.add(stringifyUrlIdOrg(docId, scope.org));
// Remove any cache keys that start with any of the prefixes.
for (const key of this._docAuthCache.keys()) {
  const name = key.split(" ", 1)[0];
  if (names.has(name)) { this._docAuthCache.delete(key); }
}
```
Post-commit deferral (pattern used by every mutation):
```ts
this.caches?.addInvalidationDocAccess(notifications, [doc.id]);
...
for (const notification of notifications) { await notification(); }
```

**Flow:** reads → `getDocAuthCached` fills LRU (promise memoization collapses concurrent misses); mutations (`updateOrgPermissions` :2196, `updateWorkspacePermissions` :2298, `updateDocPermissions` :2372, `moveDoc` :2723, `updateDocument` :1975, `setDocPrefs` :3435) queue `addInvalidationDocAccess(notifications, docIds)` — for hierarchy changes the affected set comes from `_getDocsInheritingFrom(manager, {orgId|wsId})` (:5047–5064, 3-level group_groups walk). `HomeDBCaches._getDocAccess` fetches with previewer bypass scope `{userId: previewer, flatten:true, excludeUsersWithoutAccess:true}`.
**Invariant:** The LRU caches PROMISES not values — one failed lookup poisons the slot until TTL unless callers use `mapSetOrClear` semantics in `getDoc` (:1142). Errors are cached as DocAuthResult objects (fail-closed on read of `access`). A porter who invalidates inside the transaction publishes uncommitted state to other servers via redis; the callback-list pattern exists precisely to run invalidations AFTER commit.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "should invalidate docAccess values when doc is moved" test/gen-server/lib/HomeDBCaches.ts'` → :186.
`bash -c 'grep -c "addInvalidationDocAccess" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 5.
Direct tests: `test/gen-server/lib/HomeDBCaches.ts` (redis-gated suite: expire :84, invalidate-on-access-change :132, move :186, "happens not to invalidate on user name changes" :247, cross-server :318).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"getDocAuthCached _docAuthCache HomeDBCaches flushSingleDocAuthCache addInvalidationDocAccess","limit":8,"detail":"ids"}'`

**Verdict:** ADAPT — extends existing `request-scoped-docauth-cache.md` (which stops at Authorizer/mreq layer); this capsule documents the two layers BELOW it that its "flush" instruction actually targets.
