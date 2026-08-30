<!-- capsule-v2 -->
# computed-pagination-fallback — Why is pagination silently disabled when filter/sort touch computed fields?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What happens when a paginated view's WHERE/ORDER references a lookup, rollup, or formula field?

## Computed fields in the base predicate disable the BASE limit
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:referencesComputedField` (:589-603) + `isComputedField` (:532-544) + fallback at :486-494.
**Signature:** `private referencesComputedField(fieldIds: Set<string>, fieldLookup: Map<string, FieldCore>): boolean`.
**Data Shape:** `collectRequiredFieldIds` unions `extractFieldIdsFromFilter(filter)` + sort fieldIds + defaultOrderField; record-id restriction survives even when pagination dies.

### Decisive source
```ts
if (this.referencesComputedField(requiredFieldIds, fieldLookup)) {
  // Fall back to full table scan when pagination conflicts with computed fields,
  // but still allow record-level restriction to run.
  applyPagination = false;
  if (!applyRecordRestriction) {
    return;
  }
}
```

**Flow:** gather required ids → any id resolving to a field where `isLookup || type ∈ {Rollup, ConditionalRollup, Formula}` → drop pagination → if no id-restriction either, skip BASE CTE construction completely (query runs unpaginated over the raw table).
**Invariant:** correctness beats performance: computing a lookup value requires the link CTEs which are built AFTER pagination; filtering on them pre-CTE is impossible, so the builder refuses a wrong fast path instead of producing a filtered-wrongly page. The caller gets MORE rows than requested (unpaged), never fewer.
**Probe:** static: `grep -n 'applyPagination = false' ...service.ts` → exactly :488 with that comment. Upstream spec coverage for the surrounding aggregate path lives in `record-query-builder-group-quoting.spec.ts`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"referencesComputedField","limit":5,"detail":"ids"}'
```

## Verdict
Adopt "computed-in-predicate ⇒ degrade to unpaged" as an explicit, documented fallback. Adapt the computed-field classifier to your field-type enum. Omit nothing else — the asymmetry (pagination drops, id-restriction stays) is the portable part.
