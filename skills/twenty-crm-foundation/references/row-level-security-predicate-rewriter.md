<!-- capsule-v2 -->
# row-level-security-predicate-rewriter

## Source
- Repo: `twenty-crm`
- Path: `packages/twenty-server/src/engine/twenty-orm/utils/apply-row-level-permission-predicates.util.ts` (+ `resolve-row-level-permission-record-filter.util.ts`)
- Symbol: `applyRowLevelPermissionPredicates` / `resolveRowLevelPermissionRecordFilter`
- Lines: apply util 24-92 (whole file); resolve util 14-46
- Commit: `a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0`
- Graph Node: `ext-twenty-crm.packages.twenty-server.src.engine.twenty-orm.utils.apply-row-level-permission-predicates.util.applyRowLevelPermissionPredicates`

## Signature & Data Shape
```typescript
type ApplyRowLevelPermissionPredicatesArgs<T extends ObjectLiteral> = {
  queryBuilder: WorkspaceSelectQueryBuilder<T>;
  objectMetadata: FlatObjectMetadata;
  internalContext: WorkspaceInternalContext;
  authContext: WorkspaceAuthContext;
  featureFlagMap: FeatureFlagMap;
};

export const applyRowLevelPermissionPredicates =
  <T extends ObjectLiteral>(args: ApplyRowLevelPermissionPredicatesArgs<T>): void;
```

## Decisive Source Excerpt
```typescript
const recordFilter = resolveRowLevelPermissionRecordFilter({
  internalContext, authContext, objectMetadata,
});
if (!isDefined(recordFilter)) return;              // no roles/predicates → NO clause at all

const isUpdateOrDeleteQuery =
  queryBuilder.expressionMap.queryType === 'update' ||
  queryBuilder.expressionMap.queryType === 'soft-delete' ||
  queryBuilder.expressionMap.queryType === 'delete';

applyObjectRecordFilterToQueryBuilder({
  queryBuilder,
  objectNameSingular: objectMetadata.nameSingular,
  recordFilter,
  fieldParser: new GraphqlQueryFilterFieldParser(
    objectMetadata, internalContext.flatFieldMetadataMaps),
  useDirectTableReference: isUpdateOrDeleteQuery,   // mutations can't join — hit the table direct
});

// applier:
const whereCondition = new Brackets((qb) => {
  applyFilterEntriesToWhereExpression({ whereExpression: qb, /* … */ filter: recordFilter });
});
if (queryBuilder.expressionMap.wheres.length === 0) {
  queryBuilder.where(whereCondition);
} else {
  queryBuilder.andWhere(whereCondition);
}
```

## Flow
1. Resolve the role set from auth context (`userWorkspaceRoleMap` for users, `apiKeyRoleMap` for API keys), build the intersection of per-role RLS predicate groups into ONE GraphQL-style record filter; empty/absent ⇒ emit nothing (fail-open by DESIGN — predicate maps only exist where enterprise RLS is configured).
2. Detect mutation queries (`update` / `soft-delete` / `delete`) and switch the filter walker to `useDirectTableReference` so predicates reference the physical table instead of a select-only join alias.
3. Translate the metadata-driven filter AST to SQL through `GraphqlQueryFilterFieldParser`, wrap EVERYTHING in one isolated TypeORM `Brackets` node, and append with `andWhere` when prior wheres exist (never overwrite).
4. The whole utility is `void`-returning by contract: permission enforcement happens by MUTATING the caller's query builder before execution.

## Invariant
Every RLS predicate lands inside isolated `Brackets` combined via `andWhere`, so developer-supplied WHERE conditions can never escape the permission boundary via OR-precedence. Mutation queries must use direct table references because TypeORM update/delete builders have no select alias to hang joins on. No resolvable filter ⇒ no clause (the feature is opt-in via predicate configuration, not a default deny).

## Direct-Test Probe
- File: `packages/twenty-server/src/engine/twenty-orm/utils/__tests__/apply-row-level-permission-predicates.util.spec.ts`
- Suite: `describe('applyRowLevelPermissionPredicates')` (:98)
- Pins: `it('uses where when the query builder has no existing where clause')` (:105), `it('appends with andWhere so it never resets an existing where clause')` (:113), `it('references the column through the table alias for a select query')` (:120), `it('emits nothing when there is no record filter')` (:136), `it('emits nothing when the record filter is empty')` (:142)

```bash
grep -n 'it(' packages/twenty-server/src/engine/twenty-orm/utils/__tests__/apply-row-level-permission-predicates.util.spec.ts   # => :105,:113,:120,:136,:142
```

## Graph Query
```bash
echo '{"project":"ext-twenty-crm","name_pattern":"applyRowLevelPermissionPredicates"}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the bracket-isolated andWhere RLS applier together with the mutation-query direct-table-reference toggle.
