<!-- capsule-v2 -->
# Handler dispatch core — how does one registry route filter/sort/select per (uidt × dbClient), and what do apply vs verify disagree on?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How is a column's type+dialect routed to its handler, and why does an orphaned filter row get skipped by reads but FAIL verification?

## HANDLER_REGISTRY + FieldHandler orchestrator
**Path/Symbol:** `packages/nocodb/src/db/field-handler/index.ts:HANDLER_REGISTRY` (:106-288), `FieldHandler.getHandler` (:326-336, private, CLIENT_DEFAULT fallback), `applyFilters` (:370-426), `verifyFiltersSafe` (:493-539).
**Signature:** `getHandler(uiType: UITypes, dbClient: ClientType): FieldHandlerInterface` — `dbHandlers?.[dbClient] ?? dbHandlers?.[CLIENT_DEFAULT]`, else `undefined`; `applySort` alone falls back to `new GenericFieldHandler()` (:469).
**Data Shape:** Registry = `Partial<Record<UITypes, Partial<Record<ClientType | '_default', ctor>>>>`; empty objects (`ForeignKey`, `GeoData`, `AutoNumber`, `Geometry`, `SpecificDBType`) mean "no handler" → parse paths return `{value}` untouched.

### Decisive source
```ts
// :402-406 — APPLY path: skip orphans (defense-in-depth):
// Skip filters whose column was deleted — defense-in-depth against
// orphaned filter rows that weren't cleaned up on column deletion.
if (!column) { continue; }
// :506-515 — VERIFY path: fail them loudly (RLS leak guard):
// Fail verification if the filter's column was deleted. This blocks the
// query rather than silently skipping — critical because filters may be
// RLS policies, and skipping those would leak restricted rows.
if (!column) {
  traverseResult.push({ isValid: false,
    errors: [`Filter references a non-existent field (fk_column_id: ...)`] });
}
```

**Flow:** applyFilter resolves dbClient from `knex.clientType() ?? knex.client.config.client` → handler.filter returns deferred `{clause, rootApply}` → applyFilters collects indexed entries (null filters skipped; groups recurse via applyFilterGroup) → clause application replays in index order through `getLogicalOpMethod(logical_op)` mapping or→orWhere / and→andWhere / not→whereNot / default→where. verifyFiltersSafe traverses the SAME tree via traverseFilters (handles array-of-array nesting) then folds all invalid results into one aggregate.
**Invariant:** (1) The apply-skip vs verify-fail asymmetry is intentional — making both skip would let RLS policies vanish silently after a column drop. (2) `getLogicalOpMethod` lowercases before matching, so 'OR'/'AND' from clients still map. (3) rootApply runs separately AFTER clause composition — order between the two lists is preserved by index sort.
**Probe:** No direct unit tests for this class at pin (controller specs are construction-only). Deterministic probe: search_graph resolves `FieldHandler.getHandler Method ... index.ts 326-336` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "FieldHandler applyFilters", limit: 10 });
```

## Verdict
Adopt the two-key registry with _default fallback and the apply-vs-verify orphan asymmetry; adapt the op-method mapping to your builder; omit the commented-out nested-parseDbValue block (:701-711). Caveat: no dedicated upstream tests at pin.
