<!-- capsule-v2 -->
# upsert-where-condition-builder — How do you find candidate conflicts for a whole batch in ONE query?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** How are per-record match conditions collapsed into a bounded set of SQL predicates?

## upsert-where-condition-builder
**Path/Symbol:** `packages/twenty-server/src/engine/api/common/common-query-runners/common-create-many-query-runner/utils/build-where-conditions.util.ts:buildWhereConditions` (:62-117).
**Signature:** `(records: Partial<ObjectRecord>[], conflictingFieldGroups: ConflictingFieldGroup[]): Record<string, FindOperator>[]` (TypeORM where-shape; `In`/`Equal` operators).
**Data Shape:** one condition object per "matchable key": single-column groups collapse the WHOLE batch into one `{col: In(distinctValues)}`; composite groups emit one AND-of-equalities per record (`{a: Equal(v1), b: Equal(v2)}`), deduplicated by a canonical JSON key.

### Decisive source
```ts
const buildCompositeConditionKey = (conditionEntries) => {
  const sortedEntries = [...conditionEntries].sort(([columnA], [columnB]) =>
    columnA.localeCompare(columnB),
  );
  return JSON.stringify(sortedEntries);
};
```
(:14-22 — sort-by-column BEFORE stringify makes the dedupe key order-insensitive.)

**Flow:** for each group → single property ⇒ gather defined values across all records, `Set`-dedup, skip if none remain (:28-41) → composite ⇒ per record collect `[column, value]` pairs; ANY missing member drops that record from that group's probe (`buildCompositeConditionEntries` returns undefined :49-54) → dedupe via sorted-key → push Equal-folded condition. The runner ORs every condition together inside one Brackets block (`common-create-many-query-runner.service.ts:427-443`), and adds `.withDeleted()` so soft-deleted rows still claim their unique keys (:457-462).
**Invariant:** a partial composite key must NOT match (three of four columns equal is not uniqueness); NULL/undefined never participates (`isDefined` filters). Probe breadth is bounded: single-column groups cost one IN-list regardless of batch size; only genuinely distinct full keys multiply. Soft-deleted rows MUST be probed or an insert would violate the unique index instead of reviving/updating the row.
**Probe:** `grep -c 'In(distinctValues)' packages/twenty-server/src/engine/api/common/common-query-runners/common-create-many-query-runner/utils/build-where-conditions.util.ts` → 1; direct spec: `src/engine/api/common/common-query-runners/common-create-many-query-runner/utils/__tests__/build-where-conditions.util.spec.ts` ("collapses a single-column group into one IN condition", "skips a composite group for a record missing part of the key").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "buildWhereConditions In Equal", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt batch-level conflict probing (one IN per scalar key, one AND-tuple per distinct composite key, missing-member exclusion, withDeleted). Adapt operator construction to your query builder. Omit TypeORM FindOperator specifics; keep the sorted-canonical-key dedupe trick.
