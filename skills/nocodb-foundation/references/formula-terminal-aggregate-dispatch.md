<!-- capsule-v2 -->
# Terminal value aggregation — how does the chain's LAST column decide between plain select, aggregate fn, and recursion?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When the nested chain reaches a non-Lookup terminal column, how does each uidt produce its scalar expression — and when does it become an aggregate function call?

## terminal switch by uidt
**Path/Symbol:** `packages/nocodb/src/db/formulav2/lookup-or-ltar-builder.ts` terminal switch (:527-867).
**Signature:** `switch (lookupColumn.uidt)` → arms: Links/Rollup (:528-560), LinkToAnotherRecord (:561-713), Formula (:714-753), Barcode/QrCode (:754-778), CreatedBy/LastModifiedBy/CreatedTime/LastModifiedTime (:779-800), Attachment (:801-846), default (:847-866).
**Data Shape:** Multi-row terminals wrap `getAggregateFn(fn)({qb, knex, cn})` in `.wrap('(',')')`; single-row terminals `select(...)` a parenthesized raw.

### Decisive source
```ts
// :544-558 — the isArray fork is THE aggregation decision:
if (isArray) {
  const qb = selectQb;                       // capture BEFORE reassignment
  selectQb = (fn) =>                         // builder becomes a FUNCTION
    knex.raw(
      getAggregateFn(fn)({ qb, knex, cn: knex.raw(builder).wrap('(', ')') }),
    ).wrap('(', ')');
} else {
  selectQb.select(knex.raw(builder).wrap('(', ')'));
}
// :608-615 — display col resolved from the TERMINAL LTAR, not hop one:
// Must be resolved from the terminal LTAR (lookupColumn), whose
// related table the joins below read from — resolving from the
// first-hop relationCol picked a column of the wrong table.
const nestedDisplayCol = await getDisplayValueOfRefTable(context, lookupColumn);
```

**Flow:** Links/Rollup delegate to genRollupSelectv2 under prevAlias; LTAR adds one more relation join and selects its display column (MM arm sets `isArray = true` unconditionally); Formula recurses via `_formulaQueryBuilder` with parentColumns extended through `CircularRefContext.cloneAndAdd({id, title, table})` for cycle detection; QR/Barcode select their VALUE column; user/time family resolves alias refs via getRefColumnIfAlias; Attachment has a PG concat special case; everything else falls to the plain `${prevAlias}.${column_name}` arm.
**Invariant:** (1) The `(fn) =>` closure captures `selectQb` in a local BEFORE overwriting the outer variable — capturing lazily would recurse infinitely. (2) The Formula arm's cloneAndAdd is the cycle guard: without threading id/title/table into parentColumns, self-referencing formulas loop forever. (3) The MM-LTAR arm's `cn = ...` assignment sits AFTER its case block (:691) so it applies to ALL three relation types — moving it inside the case breaks BT/HM. (4) Attachment+PG+concat builds `jsonb_agg(__elem)::text FROM (...) t CROSS JOIN LATERAL jsonb_array_elements(...)` because string-concatenating JSON arrays produces garbage.
**Probe:** No unit tests upstream. Deterministic probe: sed 685-700 shows the cn = knex.raw('??.??') assignment outside the switch arms' braces; search_graph resolves `getDisplayValueOfRefTable` line-exact in generateLookupSelectQuery.ts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getAggregateFn", limit: 5 });
// formula-query-builder.helpers.ts owns the per-dialect aggregate vocabulary
```

## Verdict
Adopt the isArray→aggregate-function contract and terminal-LTAR display resolution; adapt the aggregate vocabulary; omit the stray `console.log('fn', fn, knex.clientType())` (:807) left in the Attachment arm. Caveat: no direct tests at pin.
