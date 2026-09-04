<!-- capsule-v2 -->
# Import action-bundle lifecycle — who opens and closes the user-action bundle across a multi-request import?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** An import spans several HTTP round-trips (transform preview → finish/cancel). Where does the undo bundle open, where must it close, and what breaks if you "fix" the asymmetry?

## importFiles opens a bundle it NEVER closes; finishImport/cancelImport close it; cancel closes one it never opened
**Path/Symbol:** `app/server/lib/ActiveDocImport.ts`: `importFiles` (69–76), `finishImportFiles` (82–96), `cancelImportFiles` (107–113), `oneStepImport` (220–227), `_removeHiddenTables` (609–613); upload ownership gate `globalUploadSet.getUploadInfo(uploadId, makeAccessId(userId))`.
**Signature:** `importFiles(docSession, dataSource, parseOptions, prevTableIds): Promise<ImportResult>`; `finishImportFiles(..., importOptions)`; `cancelImportFiles(docSession, uploadId, prevTableIds)`.
**Data Shape:** hidden tables named `"GristHidden_import"` (sanitized by AddTable); `prevTableIds` carries them from call to call.

### Decisive source
```ts
// importFiles — starts bundling, deliberately no matching stop:
this._activeDoc.startBundleUserActions(docSession);
await this._removeHiddenTables(docSession, prevTableIds);
...
return this._importFiles(docSession, uploadInfo, dataSource.transforms, { parseOptions }, true);

// finishImportFiles / oneStepImport — symmetric try/finally:
try { ... await globalUploadSet.cleanup(dataSource.uploadId); return importResult; }
finally { this._activeDoc.stopBundleUserActions(docSession); }

// cancelImportFiles — stops a bundle it never started in THIS request:
await this._removeHiddenTables(docSession, prevTableIds);
this._activeDoc.stopBundleUserActions(docSession);
await globalUploadSet.cleanup(uploadId);
```

**Flow:** client calls importFiles → server creates hidden staging tables inside an OPEN bundle (all intermediate churn collapses into one undo step visible to other collaborators as nothing) → response returns → later finish/cancel request lands on the same ActiveDoc and closes the bundle while deleting hidden tables and cleaning the upload. The bundle therefore intentionally survives BETWEEN requests, held by session identity. Upload access is keyed by `makeAccessId(userId)` so only the importing user's session can resolve the upload.
**Invariant:** the asymmetry is the mechanism — closing the bundle at the end of importFiles would expose every hidden-table rewrite as its own undo entry and break preview re-imports; conversely finish/cancel MUST close or every later edit of that doc joins the import's undo group forever. Hidden-table removal is idempotent-guarded (`length !== 0`) and runs first in all three paths.
**Probe:** exercised end-to-end via doc-worker import suites (`test/server/lib/ActiveDocImport.js` legacy harness) and `test/server/lib/BundleActions.ts` for the underlying bundle semantics; direct per-method unit test absent at this pin — caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "startBundleUserActions stopBundleUserActions importFiles cancelImportFiles", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt when a long interactive operation must look atomic to collaborators: open the transaction-like bundle on request A, close on request B/C, and treat crash recovery (bundle leak) explicitly elsewhere. Adapt upload-ownership tokens to your storage layer. Do NOT "fix" the unpaired start/stop without redesigning the preview flow.
