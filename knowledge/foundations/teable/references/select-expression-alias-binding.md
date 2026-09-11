<!-- capsule-v2 -->
# select-expression-alias-binding — Why are every computed SELECT item emitted as knex.raw with an explicit alias object?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does buildSelect attach dbFieldName aliases without triggering knex placeholder parsing?

## qb.select({ [dbFieldName]: knex.raw(expr) }) — never a bare string containing '?'
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:buildSelect` (:633-682, binding at :663-673); preserved system columns first (:654-658).
**Signature:** `private buildSelect(qb, table, state, projection?, rawProjection?, preferRawFieldReferences?, preferStoredLookupFields?)`.
**Data Shape:** system columns (`preservedDbFieldNames`: __id etc.) selected as plain qualified strings; every visitor-returned string goes through `this.knex.raw(result)` keyed by an alias OBJECT.

### Decisive source
```ts
for (const field of preservedDbFieldNames) {
  qb.select(`${alias}.${field}`);
}
...
if (typeof result === 'string') {
  // Always alias via raw to avoid Knex placeholder detection on expressions (e.g., regex with '?')
  const aliasBinding = field.dbFieldName;
  qb.select({ [aliasBinding]: this.knex.raw(result) });
} else {
  qb.select({ [field.dbFieldName]: result });
}
```

**Flow:** ready-link ids derived from joined CTEs (only CTE-backed lookups may reference their CTE columns) → FieldSelectVisitor per ordered field → string results aliased via raw; non-string (knex Raw) results aliased directly.
**Invariant:** passing a computed SQL string directly to `qb.select("expr AS name")` would let knex scan for `?` bind placeholders inside regex/JSON operators and corrupt the query; the raw+alias-object form is the only safe channel. Selection map registration happens inside the visitors, so WHERE/ORDER BY reuse identical expressions.
**Probe:** static byte-exact: `grep -n 'Always alias via raw' apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts` → :662; upstream spec `record-query-builder-group-quoting.spec.ts` asserts no bare unquoted identifiers leak into compiled SQL.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildSelect","limit":5,"detail":"ids"}'
```

## Verdict
Adopt raw-with-alias-object as the only expression channel. Adapt for your query library's equivalent. Omit nothing.
