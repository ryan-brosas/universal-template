<!-- capsule-v2 -->
# link-cte-emission-choreography — What is the exact build order for a per-link-field CTE (name, stack, nested deps, join-back)?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is one link field's aggregated CTE generated, registered, and joined without cycles or double joins?

## Stack-guarded generation, pending-name registration, join after emit
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:generateLinkFieldCte` (:1989-2379); name factory `generateCTENameForField` (:718); join-back at :2368-2372.
**Signature:** `private generateLinkFieldCte(linkField: LinkFieldFieldCore): void`; CTE name `` `CTE_${getTableAliasFromTable(table)}_${field.id}` ``; CTE columns: `main_record_id`, `link_value`, `"lookup_<id>"…`, `"rollup_<id>"…`.
**Data Shape:** three reentrancy structures — `linkCteGenerationStack` (in-flight), `emittedLinkCteIds` (fully built), `pendingLinkCteNames` (name reserved before body exists).

### Decisive source
```ts
if (this.state.getFieldCteMap().has(linkField.id)) return;   // already built
if (this.linkCteGenerationStack.has(linkField.id)) return;   // in-flight cycle guard
...
this.linkCteGenerationStack.add(linkField.id);
this.pendingLinkCteNames.set(linkField.id, cteName);
try {
  ...buildLinkCte();                       // WITH <cteName> AS (...) + lookups/rollups columns
  this.state.setFieldCte(linkField.id, cteName);
  this.emittedLinkCteIds.add(linkField.id);
} finally {
  this.linkCteGenerationStack.delete(linkField.id);
  this.pendingLinkCteNames.delete(linkField.id);
}
// join-back exactly once:
if (!this.state.isCteJoined(cteName)) {
  this.qb.leftJoin(cteName, `${mainAlias}.${__ID}`, `${cteName}.main_record_id`);
  this.state.markCteJoined(cteName);
}
```

**Flow:** skip-if-built → push stack + reserve pending name → pre-generate nested foreign CTEs for lookup/rollup/display targets (`generateNestedForeignCtesIfNeeded`) → hard-guarantee pass ensuring foreign-side link CTEs exist before reference → collect `nestedJoins` via `ensureLinkDependencyForScope` (only ALREADY-EMITTED nested CTEs get LEFT JOINed; in-flight candidates are skipped) → emit `WITH` body grouped by `main_alias.__id` with relationship-specific join shape (junction / one-many FK-in-foreign / many-one symmetric-swap) → register on manager, mark emitted → single guarded leftJoin back onto the main query.
**Invariant:** a CTE may be JOINed only after it appears earlier in the WITH list (`emittedLinkCteIds.has(candidate.id)` gate :956); self-join of the CTE under construction is impossible because the stack blocks re-entry and the blocked-set hides the current link from inner visitors. Join-once via `isCteJoined`.
**Probe:** static byte-exact: `grep -n 'CTE_\${getTableAliasFromTable(table)}_\${field.id}' field-cte-visitor.ts` → :718; `grep -n 'emittedLinkCteIds.has(candidate.id)' field-cte-visitor.ts` → :956.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"generateLinkFieldCte","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the whole choreography for any recursive link-aggregation builder. Adapt the CTE naming scheme and alias derivation (`t_<safeId>`). Omit the DEBUG_NESTED_CTE env logging.
