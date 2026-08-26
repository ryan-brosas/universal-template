<!-- capsule-v2 -->
# conditional-lookup-warning-degradation — What happens when a conditional lookup's CTE cannot be generated at SELECT time?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do the visitors behave on a missing conditional CTE (warn vs throw vs null)?

## Loud console.warn + typed NULL — never an exception out of query building
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:visitLookupField` (:428-442) + generation guards `generateConditionalLookupFieldCteForScope` (:1620-1668 warn ladder); reader twin `field-select-visitor.ts` (:266-296).
**Signature:** warn payloads embed field id/name + available CTE keys; return is always `this.dialect.typedNullFor(field.dbFieldType)`.
**Data Shape:** generation skip reasons enumerated one warn per cause: hasError / missing foreignTableId|lookupFieldId / foreign table absent / target field absent; each logs `[ConditionalLookup] Skipping CTE generation for field ...`.

### Decisive source
```ts
const cteName = this.fieldCteMap.get(field.id);
if (!cteName) {
  const fieldCteMapKeys = Array.from(this.fieldCteMap.keys());
  console.warn(
    `[ConditionalLookup] CTE not found for field ${field.id} (${field.name}). ` +
    `Available CTEs: [${fieldCteMapKeys.join(', ')}]. Returning NULL::${field.dbFieldType}`
  );
  return this.dialect.typedNullFor(field.dbFieldType);
}
```

**Flow:** build() asks for options → missing/invalid → warn + skip (no CTE registered) → selection later finds no CTE → second warn (reader-side, listing available keys) + typed NULL cell. The query still returns rows; only the broken column nulls.
**Invariant:** degradation is two-stage and both stages are observable (warn text differs), so operators can distinguish config-time skips from read-time misses. Nothing in this plane throws — contrast with rollupAggregate's unsupported-fn throw, which guards a programming error rather than data state.
**Probe:** static byte-exact: `grep -c '\[ConditionalLookup\]' field-cte-visitor.ts field-select-visitor.ts` → 5 + 3 warns.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"ConditionalLookup CTE not found","limit":5,"detail":"ids"}'
```

## Verdict
Adopt warn+typed-null as the failure contract for optional computed columns. Adapt log channel. Omit nothing.
