<!-- capsule-v2 -->
# Query-shape literal exclusion — how do you record query analytics without ever storing user query values?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does the observation pipeline guarantee that raw search strings and filter values never enter shapes, snapshots, or persisted windows?

## Recursive forbidden-key veto BEFORE schema validation
**Path/Symbol:** `packages/v2/table-query-ops/src/domain.ts`: `containsForbiddenLiteralKey` (:329-339), `forbiddenLiteralKeys` (:318-327), `TableQueryShape.create` (:463-497), `TableSearchVectorShape.create` (:177-197), `tableSearchVectorShapeSchema` (:160-172).
**Signature:** `containsForbiddenLiteralKey(input: unknown): boolean`; `TableQueryShape.create(raw: unknown): Result<TableQueryShape, DomainError>`.
**Data Shape:** forbidden keys = `value | values | literal | literals | raw | rawValue | searchValue | filterValue`. Veto runs on the RAW input (pre-zod), recursing through arrays and nested objects; error codes: `table_query_ops.shape_contains_literal`, generic message variant for search-vector shapes.

### Decisive source
```ts
const containsForbiddenLiteralKey = (input: unknown): boolean => {
  if (input == null || typeof input !== 'object') return false;
  if (Array.isArray(input)) return input.some(containsForbiddenLiteralKey);
  return Object.entries(input as Record<string, unknown>).some(
    ([key, value]) => forbiddenLiteralKeys.has(key) || containsForbiddenLiteralKey(value)
  );
};
```

**Flow:** create() → literal veto (fail fast, code `…shape_contains_literal`) → zod schema validation (closed enums for queryKind/operatorFamily/searchMode/buckets) → post-parse normalization: `searchedFieldIds` deduped via Set and SORTED lexicographically, `fieldCount` overwritten to the deduped length → frozen private-constructor instance exposed only through `snapshot()`/accessors.
**Invariant:** A shape carries COUNTS, FIELD IDS, buckets, and enums — never values. The veto fires even when zod would silently strip an unknown `value` key: stripping is not enough because downstream hashing must be able to trust absence. Search-vector shapes additionally require `fieldCount === coveredFieldIds.length`.
**Probe:** `packages/v2/table-query-ops/src/domain.spec.ts:52` "rejects raw query literals"; :65 "captures full-text search shape without raw search values"; :131/:146 for the search-vector twins.
**Coverage caveat:** none — direct vitest specs pin all four vetoes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableQueryShape create containsForbiddenLiteralKey forbiddenLiteralKeys", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the veto-before-validate ordering and the closed-vocabulary shape model wholesale (it is what makes query analytics safely persistable); adapt the forbidden-key set to your own DTO vocabulary; omit teable's specific enum members. Direct tests exist upstream; keep them when porting.
