<!-- capsule-v2 -->
# moveDoc cross-org choreography — what must be re-derived when a doc changes workspaces, and especially orgs?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Why does moving a doc touch aliases, inheritance AND guest groups on both sides?

## Owner-only move re-points group inheritance to the destination workspace; an org change additionally wipes urlId aliases and repairs guests at 2–4 nodes
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `moveDoc` (:2638–2728), alias wipe on org change (:2693–2700), inheritance re-point loop (:2690–2692), guest repair block (:2712–2721), `_checkForUrlIdConflict` (:3913–3949).
**Signature:** `moveDoc(scope: DocScope, wsId: number): Promise<QueryResult<PreviousAndCurrent<Document>>>` — requires OWNER on doc + ADD on destination.
**Data Shape:** Guards: disabled doc → 403 "Document is disabled"; same-workspace → 400 "doc is already in destination workspace"; cross-org → `_checkRoomForAnotherDoc` + `_restrictAllDocShares` against DESTINATION features (share limits evaluated as if shares were newly added).

### Decisive source
```ts
doc.aclRules.forEach((aclRule) => {
  this._groupsManager.setInheritance(aclRule.group, workspace);
});
// If the org is changing, remove all urlIds for this doc, since there could be
// conflicts in the new org.
if (oldWs.org.id !== doc.workspace.org.id) {
  doc.urlId = null;
  await manager.delete(Alias, { doc: doc.id });
}
// Forcibly remove the aliases relation from the document object, so that TypeORM
// doesn't try to save it. It isn't safe to do that because it was filtered by
// a where clause.
doc.aliases = undefined as any;
```

**Flow:** `_loadDocAccess(OWNER)` → destination `_loadWorkspaceAccess(ADD)` → optional cross-org limit checks → re-point each doc group's memberGroups to the destination's matching special groups (`setInheritance` — nestParent roles only) → save [doc, aclRules, docGroups] → repair ws-guests of source AND destination (+org-guests ×2 if org changed), only when the doc had first-level users.
**Invariant:** The `doc.aliases = undefined` assignment appears in moveDoc, updateDocument, pinDoc alike — TypeORM would otherwise try to persist an aliase relation loaded under a WHERE filter and resurrect rows. urlIds are org-SCOPED (`Alias.orgId`) so cross-org moves can't preserve them; conflict grammar differs by org type (support org checks globally, personal checks across ALL personal orgs, team checks own+example org — :3921–3937). Porters who keep aliases across moves create ambiguous routing in the merged personal-org domain.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "should invalidate docAccess values when doc is moved" test/gen-server/lib/HomeDBCaches.ts'` → :186 (move is a first-class invalidation trigger).
`bash -c 'grep -n "setInheritance" app/gen-server/lib/homedb/HomeDBManager.ts | head -2'` → includes :2691 call site + :4052-ish def in GroupsManager.
Direct tests: `test/gen-server/lib/HomeDBCaches.ts` :186 suite; DocApi move tests (`test/server/lib/docapi/`).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"moveDoc setInheritance _checkForUrlIdConflict Alias _restrictAllDocShares","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — resource-move choreography generalizes to any multi-tenant system with scoped short identifiers.
