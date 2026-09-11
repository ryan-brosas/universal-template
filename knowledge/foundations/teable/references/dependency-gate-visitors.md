<!-- capsule-v2 -->
# Dependency-change gating — how do collector visitors decide WHICH specs trigger cycle checks, self-backfills, and deferred cascades without false positives?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Among 60+ table specs, what is the exact allowlist that marks a spec as dependency-affecting or backfill-requiring?

## DependencyChangeDetectorVisitor + FieldValueChangeCollectorVisitor
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/DependencyChangeDetectorVisitor.ts` whole (445L); `visitors/FieldValueChangeCollectorVisitor.ts` — visitTableUpdateFieldType (:200–251), visitUpdateLinkRelationship (:471–474).
**Signature:** both implement ITableSpecVisitor<void> with per-instance mutable state: detector = `{needsCheckValue, dependencyChangedFieldIdSet}`; collector = `{selfBackfillFieldIdSet, valueChangedFieldIdSet, deferredBackfillFieldIdSet, dbStorageTypeChanged}`.
**Data Shape:** sets are Map-keyed by fieldId string (insertion-order dedup — ids come out in first-seen order, pinned by test).

### Decisive source
```ts
// Detector MARK list (everything else is an explicit ok() no-op):
visitTableAddField/AddFields  → only COMPUTED types: formula, lookup, rollup,
                                conditionalRollup, conditionalLookup, link
visitTableUpdateFieldType     → always mark newField.id()
visitUpdateFormulaExpression  → mark fieldId
visitUpdateLinkConfig         → mark fieldId   (lookupFieldId/symmetric changes)
visitUpdateLookupOptions      → mark fieldId
visitUpdateRollupConfig       → mark fieldId
visitUpdateConditionalRollup/LookupConfig → mark WITHOUT fieldId (spec lacks it)

// Collector triage for type conversions:
this.addValueChanged(fieldId);                    // dependents must cascade
if (newIsComputed) this.addSelfBackfill(fieldId); // recompute own column too
if (oldVT.cellValueType ≠ newVT || oldVT.isMultipleCellValue ≠ newVT)
  this.dbStorageTypeChanged = true;               // DISTINCT filter becomes unsafe
```

**Flow:** repository update() accepts the spec once and fans it through all three collectors; detector output scopes the dependency-graph load (`requiredFieldIds`) before cycle detection; collector sets drive immediate vs deferred backfill; formatting-only updates (showAs, timeZone, color) are deliberately unmarked in BOTH visitors.
**Invariant:** marking is additive and idempotent within one visitor instance — never reset between specs in the same mutation batch; conditional rollup/lookup config changes mark WITHOUT a fieldId so the whole base graph gets checked (conservative because the spec API exposes no id); link relationship changes are DEFERRED (post-commit replay) not immediate.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/DependencyChangeDetectorVisitor.spec.ts:17 'marks only dependency-producing added fields and de-duplicates field ids'`, :39 'marks dependency-affecting update specs and supports conditional config checks without field ids', :66 exhaustive no-op method list.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "DependencyChangeDetectorVisitor markForCheck FieldValueChangeCollectorVisitor addDeferredBackfill hasDbStorageTypeChange", limit: 10 });
```

## Verdict
Adopt reverse-allowlist spec classification (explicit no-ops + tiny mark lists), string-id insertion-order dedup sets, the computed-triage triple (value-changed/self-backfill/storage-type-drift), and conservative no-id marking; adapt the spec taxonomy to host command types; omit teable's specific type strings.
