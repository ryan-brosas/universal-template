<!-- capsule-v2 -->
# Lookup filter subquery shapes — how do HM, BT, and MM lookups each build their containment row-set (and where does the MM window limit bolt on)?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What does the inner subquery select per relation type, which column does the outer IN bind, and why does the MM branch rank junction pairs with ROW_NUMBER?

## LookupGeneralHandler.filter three forks
**Path/Symbol:** `packages/nocodb/src/db/field-handler/handlers/lookup/lookup.general.handler.ts` — orphan guard :88-103; allof collection semantics :105-155; HM :202-301; BT :303-386; MM :388-569.
**Signature:** `filter(knex, filter, column, options) → FilterOperationResult` where clause = `whereIn/whereNotIn(<outer key>, qb)`.
**Data Shape:** HM: qb selects child FK; outer binds parent PK. BT: qb selects parent PK; outer binds local child FK (`comparisonColumnName`). MM: qb selects junction mmChildColumn joined to related rows; outer binds the LOCAL table's childColumn.

### Decisive source
```ts
// :105-108 — allof over a LOOKUP is set membership across related rows:
// Collection semantics for allof/nallof:
// A lookup exposes a set of values from all related rows. allof [A,B] means
// the combined set must contain A AND B — not that a single row has both.
// Split into individual anyof/nanyof sub-filters and combine accordingly.
// :440-446 — the MM link-filter alias incident:
// Link conditions on the lookup filter the RELATED records ... Passing
// `childBaseModel`/`alias` (the filtered base table and the junction alias)
// emitted `<junction_alias>.<related_column>`, a column that does not exist
// on the junction table -> Postgres 42703. The HM/BT branches already pass
// the matched (model, alias) pair.
```

**Flow:** guard orphans (no colOptions / colOptions.error / missing relation → EMPTY clause keeps query valid) → resolve relationType (OO via meta?.bt; isMMOrMMLike forces MM) → per fork: select the join key, apply nestedConditionJoin for the looked-up value condition (with negatedMapping pre-flip), extractLinkRelFiltersAndApply at the MATCHED alias, aliased soft-delete filter → PG-only window limit when config exists → return deferred clause binding the outer key.
**Invariant:** (1) MM window limit ranks `(childFk, parentFk)` PAIRS — ROW_NUMBER PARTITION BY junction child-FK ORDER BY sort bits + deterministic child-FK tiebreaker (:499-503), takeLast implemented by flipping sort directions rather than descending the rn comparison. (2) allof splits into AND-of-anyofs and nallof into OR-of-nanyofs — implementing "contains all" as one LIKE-conjunction would demand single-row co-occurrence. (3) The PG-42703 comment pins the rule: link filters always ride the (related model, its alias in THIS subquery) pair.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "Postgres 42703" (:445); search_graph resolves `LookupGeneralHandler.filter Method ... lookup.general.handler.ts 69-571` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "LookupGeneralHandler filter", limit: 5 });
```

## Verdict
Adopt the fork table + empty-clause orphan policy + pair-ranked window; adapt key naming; omit the dead recursive CTE branches. Caveat: no direct tests at pin.
