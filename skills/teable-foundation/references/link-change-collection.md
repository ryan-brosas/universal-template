<!-- capsule-v2 -->
# LinkChangeCollection — classify add/remove/replace/reorder and collect exclusivity constraints

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does teable detect what changed on a link field (add/remove/replace/reorder/none) and which newly-added foreign records need an exclusivity check?

## Link change + exclusivity collection
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/visitors/LinkChangeCollectorVisitor.ts` (76-387) and `LinkExclusivityConstraintCollector.ts` (104-300).
**Signature:** `LinkChangeCollectorVisitor.create({recordId, existingLinkIds, newRawValue})` → `visitLinkField` → `{hasChange, linkChange?}`; `LinkExclusivityConstraintCollector.create({recordId, existingLinkIds, newRawValue})` → `{hasConstraint, constraint?}`.
**Data Shape:** `LinkChange = { fieldId, changeType, relationship, isOneWay, symmetricFieldId?, symmetricTableId?, addedForeignRecordIds, removedForeignRecordIds, currentForeignRecordIds }` (types in `record/computed/types/UpdateTrigger.ts`).

### Decisive source
```ts
const classifyLinkChange = (field, existingIds, newIds): LinkChangeType => {
  // size changed → detect add/remove; same size → set-diff → replace; same set → order check
  if (existingIds.length !== newIds.length) { /* add / remove / replace */ }
  // same size: different set → replace
  // same set: if hasOrderColumn or usesJunction → reorder on order mismatch, else none
  if (field.hasOrderColumn() || usesJunction) {
    const sameOrder = existingIds.every((id, index) => id === newIds[index]);
    if (!sameOrder) return 'reorder';
  }
  return 'none';
};
```

**Flow:** normalize new raw value to `{id}` items (invalid item → validation error) → classify → build LinkChange with symmetric field/table info (for two-way links) and added/removed/current RecordIds → merge into a `CollectedLinkChanges` (linkChanges + relationChangeFieldIds + affectedForeignRecords grouped by table). Exclusivity collector: only for `requiresExclusiveForeignRecord()` fields; computes newly-added ids (not in existing); builds a constraint with `usesJunctionTable = relationship==='oneMany' && isOneWay`.

**Invariant:** `mergeCollectedLinkChange` adds BOTH removed and added foreign records to `affectedForeignRecords` (removed need their symmetric link updated; added need symmetric + dependent lookups); reorder is treated as a relation change (refreshes stored link values) but not an exclusivity constraint.

**Probe:** `record/visitors/LinkChangeCollectorVisitor.spec.ts`, `record/visitors/LinkExclusivityConstraintCollector.spec.ts` — pin the classification matrix and exclusivity gate.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "classifyLinkChange LinkChangeCollectorVisitor addedForeignRecordIds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the classification ladder and the affected-records merge (both removed+added). Adapt the LinkChange type shape. Omit nothing portable. Probes pinned to the real spec suites.
