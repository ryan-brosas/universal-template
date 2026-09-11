<!-- capsule-v2 -->
# Doc lifecycle quartet — why do download, recover, replace, and assign refuse the normal withDoc wrapper?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** When must document-lifecycle endpoints avoid creating/loading an ActiveDoc through the standard route wrapper, and what per-endpoint ladders replace it?

## Four bespoke routes use bare throttled/expressWrap with hand-rolled ActiveDoc handling because their semantics ARE about doc state, not doc content
**Path/Symbol:** `app/server/lib/DocApi.ts` — `GET /download` (:660–698), `POST /recover` (:886–895), `POST /replace` (:1021–1076), `POST /assign` (:992–1017).
**Signature:** all four are `throttled(async (req,res)=>…)` or expressWrap'd; each calls `this._getActiveDoc`/`_getActiveDocIfAvailable` EXPLICITLY where needed.
**Data Shape:** `/download`: `?dryrun|dryRun`; owner check via `_isOwner(req, {acceptTrunkForSnapshot: true})`. `/recover`: body `{recoveryMode?: boolean}`. `/replace`: body `{sourceDocId?, snapshotId?, resetTutorialMetadata?}` → `DocReplacementOptions`. `/assign`: `?group` + `specialPermit.action === "assign-doc"`.

### Decisive source
```ts
// /download — broken docs must stay downloadable:
if (await this._isOwner(req, { acceptTrunkForSnapshot: true })) {
    if (dryRun) { dryRunSuccess(); return; }
    try { // "We carefully avoid creating an ActiveDoc ... in case it is broken"
      return await this._docWorker.downloadDoc(req, res, this._docManager.storageManager, filename);
    } catch (e) {
      if (e.message?.match(/does not exist yet/)) {          // never-materialized doc:
        await this._getActiveDoc(req);                       // materialize once...
        return this._docWorker.downloadDoc(...);             // ...then retry exactly one
      } else { throw e; }
    }
}
// non-owner ladder: LOAD doc as ActiveDoc → activeDoc.canDownload(session) else 403 → stream.
```
**Flow:** `/download`: owners bypass ActiveDoc entirely (broken-doc recovery path; single retry after forced materialization on "does not exist yet"), non-owners load + canDownload gate. `/recover`: owner-gated `setRecovery(docId, mode ?? true)` then fresh `fetchDoc(..., recoveryMode)` reports effective flag. `/assign`: admin/housekeeping frees a misplaced doc — compare workerGroup vs docGroup, flush, `interruptAllClients()`, `setMuted()`, `shutdown()`, `releaseAssignment` (mute makes concurrent requests 503 instead of hang). `/replace`: confirm+forward-flush the SOURCE doc on its own worker (`dryrun=1` download probe first), optional tutorial-metadata reset in a DB transaction, then `activeDoc.replace`.
**Invariant:** these endpoints manipulate the doc's EXISTENCE/placement, so unconditionally constructing an ActiveDoc could fail precisely when the endpoint must succeed (corrupt file, wrong worker). The one-retry ladder on "does not exist yet" is bounded — never loop. Cross-worker operations go through `forwardDocApiRequest` to the source's internal URL, never direct storage access.
**Probe:** `test/server/lib/docapi/DocApiDocuments.ts:68–77` ("allows assignments" + support-user denial + housekeeping bypass) and DocApiDownloads suite (export paths); coverage caveat: the broken-doc retry ladder is source-pinned only.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "downloadDoc does not exist yet setRecovery releaseAssignment forwardDocApiRequest replace", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt "lifecycle routes skip the resource-loading wrapper" for any API that manages availability of a lazily-loaded resource. Adapt the mute/shutdown dance to your eviction model. Omit tutorial/fork metadata branches unless porting Grist's fork system wholesale.
