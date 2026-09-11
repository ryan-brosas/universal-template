<!-- capsule-v2 -->
# IsPersistedAsGeneratedColumn — which computed fields are real generated columns

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** For each computed field type, is it persisted as a Postgres generated column (so writes must be skipped) or a normal column (so the app must write it)?

## Persisted-as-generated-column visitor
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/isPersistedAsGeneratedColumn.ts` (whole file, 17-94).
**Signature:** `isPersistedAsGeneratedColumn(field): Result<boolean, DomainError>` — a singleton `AbstractFieldVisitor<boolean>`.
**Data Shape:** returns `field.isPersistedAsGeneratedColumn()` for formula, createdTime, lastModifiedTime, createdBy, lastModifiedBy, autoNumber; `false` for every other type; lookup/conditionalLookup explicitly override to `false`.

### Decisive source
```ts
visitFormulaField(field) { return field.isPersistedAsGeneratedColumn(); }
visitCreatedTimeField(field) { return field.isPersistedAsGeneratedColumn(); }
visitLastModifiedTimeField(field) { return field.isPersistedAsGeneratedColumn(); }
visitCreatedByField(field) { return field.isPersistedAsGeneratedColumn(); }
visitLastModifiedByField(field) { return field.isPersistedAsGeneratedColumn(); }
visitAutoNumberField(field) { return field.isPersistedAsGeneratedColumn(); }
override visitLookupField() { return ok(false); }          // lookup NOT generated
override visitConditionalLookupField() { return ok(false); } // conditional lookup NOT generated
```

**Flow:** `field.accept(visitor)` dispatches by type; the six computed types delegate to the field's own `isPersistedAsGeneratedColumn()` (which reflects whether the DB actually materializes the column), everything else returns `false`, and lookup/conditionalLookup are hard-coded `false` (their values are derived app-side, not DB-generated).

**Invariant:** A computed field that IS a generated column must never be written by a mutation visitor (writing a generated column is a Postgres error); this is the gate the mutate/insert visitors consult via `shouldSkipComputed` / `computedField()`.

**Probe:** exercised indirectly by `record/visitors/CellValueMutateVisitor.spec.ts` `'skips non-system computed fields when setting scalar values'` (:211) and `FieldSqlLiteralVisitor.spec.ts` (lastModifiedTime/By generated-vs-not branches).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "isPersistedAsGeneratedColumn PersistedAsGeneratedColumnVisitor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the visitor-as-predicate shape and the lookup/conditionalLookup-never-generated override. Adapt the six computed type names. Omit nothing portable. Probes pinned to the real spec suites.
