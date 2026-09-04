<!-- capsule-v2 -->
# query-state-manager-scoped-selection — How is shared CTE state separated from per-scope selection state during nested query building?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do nested visitors share link-CTE registrations without polluting the outer SELECT's selection map?

## One mutable manager + a read-only-scoped child that throws on writes
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.manager.ts:RecordQueryBuilderManager` (whole 120L) + `ScopedSelectionState` (:127-190).
**Signature:** `class RecordQueryBuilderManager implements IMutableQueryBuilderState { constructor(public readonly context: 'table'|'tableCache'|'view') }`; `new ScopedSelectionState(base: IReadonlyQueryBuilderState)`.
**Data Shape:** manager owns `fieldIdToCteName: Map`, `fieldIdToSelection: Map`, `joinedCtes: Set`, `mainAlias/mainSource/originalMainSource/baseCteName`. Scoped child SHARES the CTE map and JOIN set by delegation, keeps a PRIVATE `localSelection` map, and every CTE/alias/source mutation THROWS.

### Decisive source
```ts
// ScopedSelectionState — readonly over the base CTE map:
getFieldCteMap(): ReadonlyMap<string, string> { return this.base.getFieldCteMap(); }
getSelectionMap(): ReadonlyMap<string, IFieldSelectName> { return this.localSelection; }
...
// CTE mutations are unsupported in scoped selection state
setFieldCte(_fieldId: string, _cteName: string): void {
  // intentionally no-op; CTE writes must happen on the manager
  throw new Error('setFieldCte is not supported on ScopedSelectionState');
}
```

**Flow:** service creates one manager per query (`context` stamped at construction: `'table'` vs `'tableCache'`) → FieldCteVisitor builds link CTEs registering names on the manager → for each nested foreign-table scope `createFieldSelectVisitor` wraps the SAME manager in a `ScopedSelectionState` so inner selections never leak into the outer selectionMap.
**Invariant:** exactly one writer per query; scoped contexts can READ CTEs but structurally cannot register them. `asReadonlyState` is a deliberate type-level view, not a copy.
**Probe:** upstream spec `providers/pg-record-query-dialect.spec.ts` pins dialect pieces; static: `grep -c "not supported on ScopedSelectionState" record-query-builder.manager.ts` → 6 throwing methods.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"ScopedSelectionState","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the two-class split (owning manager vs throwing scoped view) for any recursive SQL builder with shared registries. Adapt context enum values. Omit nothing — the throw-on-write design IS the seam.
