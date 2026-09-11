<!-- capsule-v2 -->
# Request-scoped docAuth cache — how do you authorize one document across many middlewares without hammering the home DB?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Where does per-request authorization state live so that canView→canEdit→handler each see ONE consistent access decision?

## Memoize on the request object itself; special permits upgrade anonymous users in one narrow branch
**Path/Symbol:** `app/server/lib/Authorizer.ts:getOrSetDocAuth` (:688–715); consumers `app/server/lib/DocApi.ts:_assertAccess` (:1798–1809), `_isOwner` (:1816–1827); invalidation `flushSingleDocAuthCache` (DocApi.ts :1900, :1922).
**Signature:** `getOrSetDocAuth(mreq: RequestWithLogin, dbManager: HomeDBManager, urlId: string): Promise<DocAuthResult>`; `_assertAccess(role: "viewers"|"editors"|"owners"|null, allowRemovedOrDisabled: boolean, req, res, next)`.
**Data Shape:** Cache slot is `mreq.docAuth` (undefined until first resolution). Middleware instances are partial applications: `canView = expressWrap(this._assertAccess.bind(this, "viewers", false))`, `canEdit` likewise, `isOwner` with `"owners"`, `canEditMaybeRemovedOrDisabled` with `(editors, true)`.

### Decisive source
```ts
if (!mreq.docAuth) {
    if (mreq.authSession?.credential) {
      mreq.docAuth = await mreq.authSession.credential.docAuth(mreq, dbManager, urlId);
    } else {
      let effectiveUserId = getUserId(mreq);
      if (mreq.specialPermit && mreq.userId === dbManager.getAnonymousUserId()) {
        effectiveUserId = dbManager.getPreviewerUserId();
      }
      mreq.docAuth = await dbManager.getDocAuthCached({ urlId, userId: effectiveUserId, org: mreq.org });
      // A permit with a user set to anonymous and linked to THIS doc upgrades to full access:
      if (mreq.specialPermit && mreq.userId === dbManager.getAnonymousUserId() &&
        mreq.specialPermit.docId === mreq.docAuth.docId) {
        mreq.docAuth = { ...mreq.docAuth, access: "owners" };
      }
    }
}
return mreq.docAuth;
```
**Flow:** first middleware in the chain pays the DB cost (`getDocAuthCached` — home-server LRU, hence "Cached") and stamps `mreq.docAuth`; every later reader (role checks, `throttle`'s billing lookup, `_isOwner`) reuses it. Role enforcement happens via `assertAccess(role, docAuth, {allowRemoved, allowDisabled})`; `showAll`/`showRemoved` scopes force `allowRemovedOrDisabled` true. After mutations that change access (delete/remove/disable), callers MUST `flushSingleDocAuthCache(scope, docId)` so the home-server cache doesn't serve stale decisions.
**Invariant:** one request = one docAuth evaluation; never bypass `getOrSetDocAuth` to fetch fresh (you'd split-brain role checks within a request). The anonymous+permit→owners upgrade applies ONLY when the permit's docId equals the resolved doc — scoped permits don't leak across documents. `_isOwner` additionally honors `{acceptTrunkForSnapshot: true}`: trunk-owner access suffices for snapshot downloads.
**Probe:** `test/server/lib/docapi/DocApiPermissions.ts` (role-matrix endpoints suite) + `DocApiSql.ts:82–105` ("POST /docs/{did}/sql has access control": non-viewer 403, viewer-promotion via `flushAuth`). Coverage caveat: the anonymous-permit upgrade branch is pinned in source, not by a named test here.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "getOrSetDocAuth assertAccess docAuth specialPermit flushSingleDocAuthCache", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt request-object memoization for any multi-stage auth pipeline — it makes "consistent within a request, fresh across requests" structural. Adapt the credential-vs-session branch to your auth stack. Omit trunk/snapshot semantics unless you have forked documents.
