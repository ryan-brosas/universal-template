<!-- capsule-v2 -->
# Soft-delete via removed_at + ON-clause filtering — why do workspace listings keep empty workspaces while hiding their deleted docs?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where is soft deletion implemented so trash views, auth caching and guest repairs all agree?

## removedAt lives on Workspace AND Document; doc visibility is filtered in the JOIN ON clause (not WHERE) so parent rows survive; showAll/showRemoved scope flags steer every read
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `_onDoc` (:4444–4453), `_applyLimit` filteredOut column (:5100–5118), `_setDocumentDeletionProperty` (:5369–5394) / `_setWorkspaceRemovedAt` (:5340–5358), getDoc removed-filter (:1144–1149), `_isForbidden` empty-trash-workspace rule (:4862–4869). Callers: `softDeleteDocument/undeleteDocument/toggleDisableDocument` (:2030–2040).
**Signature:** `_onDoc(scope)` returns the join condition: default = both not removed; showRemoved = either removed; showAll = bare key.
**Data Shape:** `workspaces_filtered_out` select: `docs.id IS NULL AND workspaces.removed_at IS [NOT] NULL` — marks workspaces that LOOK empty because all docs are hidden; `_isForbidden` drops them unless the ws itself is trashed.

### Decisive source
```ts
// This filtering is done in the "ON" clause rather than in a "WHERE" clause since we
// still want to list workspaces even if there are no docs within them. A "WHERE"
// clause would entirely remove information about a workspace with no docs.
private _onDoc(scope: Scope) {
  const onDefault = "docs.workspace_id = workspaces.id";
  if (scope.showAll) { return onDefault; }
  else if (scope.showRemoved) {
    return `${onDefault} AND (workspaces.removed_at IS NOT NULL OR docs.removed_at IS NOT NULL)`;
  } else {
    return `${onDefault} AND (workspaces.removed_at IS NULL AND docs.removed_at IS NULL)`;
  }
}
```
Single-doc path defers instead:
```ts
// We can't delegate filtering of removed documents to the db, since we'll be
// caching authentication. But ... it is very simple at the single-document level.
let qb = this._doc({ ...key, showAll: true }, { manager: transaction });
...
if (!scope.showAll && (scope.showRemoved ?
  (doc.removedAt === null && doc.workspace.removedAt === null) :
  (doc.removedAt || doc.workspace.removedAt))) {
  throw new ApiError("document not found", 404);
}
```

**Flow:** delete → `_doc(...showAll:true, REMOVE|SCHEMA_EDIT)` → raw UPDATE of one column (never entity save) → repair guests EXCLUDING soft-deleted children → cache invalidation. Undelete re-checks `_checkRoomForAnotherDoc` (features may have tightened). Permanent deletion handled by DocApi quartet (existing capsule permanent-deletion-choreography).
**Invariant:** Auth caching REQUIRES the unfiltered row (`showAll`) so a cached DocAuthResult records `removed` truthfully rather than 404ing into the cache; filtering happens post-cache in getDoc. Guest repairs and usage summaries repeat the `removed_at IS NULL` filter independently — four sites must stay in sync when porting. Disabled docs (`disabledAt`) share the same machinery but gate WRITES (updateDocument 403 "Document is disabled").

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "lists workspaces even with all docs soft-deleted" test/gen-server/lib/removedAt.ts'` → :123.
`bash -c 'grep -n "does not interfere with DocAuthKey-based caching" test/gen-server/lib/removedAt.ts'` → :355.
Direct tests: `test/gen-server/lib/removedAt.ts` (467L: hide :76, empty-ws listing :123, revert :154/:222, combine :212, caching :355, permanent flag :367–407, showAll access :409).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"_onDoc removedAt softDelete _setDocumentDeletionProperty _setWorkspaceRemovedAt","limit":8,"detail":"ids"}'`

**Verdict:** ADAPT — overlaps prior pass-9 lifecycle capsules at the DocApi layer; this capsule pins the HomeDB query-shaping half they only reference.
