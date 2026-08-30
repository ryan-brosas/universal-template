<!-- capsule-v2 -->
# Filter-operator validity sweep — how do you detect and surgically remove filter operators a field type no longer supports?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does teable repair stored filters (field options AND lookupOptions) after a field-type conversion invalidates their operators?

## checkInvalidFilterOperators / fixInvalidFilterOperator / removeInvalidFilterItems
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/link-integrity.service.ts:checkInvalidFilterOperators` (:1269–1340), `findInvalidFilterOperators` (:1341–1384), `fixInvalidFilterOperator` (:1385–1472), `removeInvalidFilterItems` (:1473–1510).
**Signature:** `removeInvalidFilterItems(filter: IFilterSet, fieldMap): IFilterSet`.
**Data Shape:** Filters nest recursively (`'filterSet' in item` discriminates group items); sources scanned: `options.filter` and `lookupOptions.filter`; validity via shared `getValidFilterOperators({cellValueType, type, isMultipleCellValue})`.

### Decisive source
```ts
const cleaned = this.removeInvalidFilterItems(options.filter, fieldMap);
const newFilter = cleaned?.filterSet?.length ? cleaned : null;   // empty ⇒ drop the whole filter
if (JSON.stringify(newFilter) !== JSON.stringify(options.filter)) {
  ops.push(
    FieldOpBuilder.editor.setFieldProperty.build({
      key: 'options',
      oldValue: options,
      newValue: { ...options, filter: newFilter },
    })
  );
}
```

**Flow:** Check walks every field's option filters, recursing nested groups and validating each leaf operator against the TARGET field's current value shape → Fix rebuilds the filter tree keeping only valid leaves, drops groups that empty out (and the entire filter when nothing survives), and emits changes ONLY through OT field-property ops into `fieldService.batchUpdateFields` — never raw SQL on options.
**Invariant:** Repairs must ride the operation pipeline so undo/webcast/meta versioning stay consistent; comparison-before-write prevents no-op op spam; an emptied filter becomes NULL rather than an always-false shell (a kept-but-empty filterSet would change lookup semantics).
**Probe:** `grep -cF 'getValidFilterOperators' apps/nestjs-backend/src/features/integrity/link-integrity.service.ts` → ≥3; direct-test anchor: `link-field.service.spec.ts` pattern (data-db routing) covers sibling service; this plane's probes are grep-pinned (no dedicated unit suite — coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "checkInvalidFilterOperators removeInvalidFilterItems getValidFilterOperators", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt recursive prune-to-valid + empty-collapses-to-null + OT-only mutation; adapt to your operator registry; omit dual options/lookupOptions scanning if you lack lookup fields.
