<!-- capsule-v2 -->
# link-relationship-join-matrix — How does the link CTE body differ per relationship (junction vs one-many vs many-one/one-one)?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What join shape + grouping does each link relationship require inside the CTE?

## Three arms: junction double-join + GROUP BY; one-many FK-in-foreign + GROUP BY; many-one/one-one direct join, NO group by
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:generateLinkFieldCte` WITH-body (:2274-2366).
**Signature:** branch keys: `usesJunctionTable` (ManyMany OR one-way OneMany — see `getLinkUsesJunctionTable` util :22-28), `relationship === OneMany`, else ManyOne/OneOne.
**Data Shape:** junction: main ⋈ junction `j` on selfKeyName ⋈ foreign on foreignKeyName; one-many: main.__id = foreign.<selfKeyName> (FK stored in FOREIGN table); many-one: `isForeignKeyInMainTable ? main.<foreignKeyName>=foreign.__id : foreign.<selfKeyName>=main.__id` (symmetric fields swap).

### Decisive source
```ts
if (usesJunctionTable) {
  this.fromTableWithRestriction(cqb, this.table, mainAlias);
  cqb.leftJoin(`${fkHostTableName} as ${JUNCTION_ALIAS}`, `${mainAlias}.__id`, `${JUNCTION_ALIAS}.${selfKeyName}`)
     .leftJoin(`${foreignTable.dbTableName} as ${foreignAliasUsed}`, `${JUNCTION_ALIAS}.${foreignKeyName}`, `${foreignAliasUsed}.__id`);
  ...nested CTE joins on `${nestedCte}.main_record_id = ${foreignAliasUsed}.__id`
  cqb.groupBy(`${mainAlias}.__id`);
} else if (relationship === Relationship.OneMany) {
  ... cqb.leftJoin(foreign..., `${mainAlias}.__id`, `${foreignAliasUsed}.${selfKeyName}`);
  cqb.groupBy(`${mainAlias}.__id`);
} else { // ManyOne / OneOne — "No GROUP BY needed for single-value relationships"
  ...
}
```

**Flow:** arm selection from field options → alias collision guard (`foreignAliasUsed = foreignAlias === mainAlias ? foreignAlias+'_f' : foreignAlias`) → joins + nested-CTE joins → GROUP BY only where rows fan out.
**Invariant:** the aggregate-vs-scalar decision upstream (`isSingleValueRelationshipContext = !(usesJunctionTable || OneMany)` passed to FieldCteSelectionVisitor) must stay consistent with the GROUP BY presence: adding GROUP BY to single-value arms breaks CASE-based cells; removing it from fan-out arms corrupts json_agg. Self-linking tables are why the `_f` alias suffix exists at all.
**Probe:** static byte-exact: `grep -n 'No GROUP BY needed for single-value' field-cte-visitor.ts` → :2352 region; upstream spec pins a many-one link end-to-end via `record-query-builder-group-quoting.spec.ts` fixture (`relationship: 'manyOne'`).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"usesJunctionTable","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the three-arm matrix incl. symmetric swap. Adapt option names. Omit nothing.
