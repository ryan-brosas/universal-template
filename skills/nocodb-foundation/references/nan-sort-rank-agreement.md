<!-- capsule-v2 -->
# NaN sort-rank agreement — how do you keep a group list and its rows ordered consistently when the DB ranks NaN as the largest number?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Cell sort and group-key sort use different SQL shapes over the same column — what invariant keeps them from disagreeing about where NaN goes?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb/src/db/field-handler/handlers/formula/formula.general.handler.ts:applySort` (:52, :63–:71) + `applyFilter` (:88–:118) + verify (:175–:186) · `packages/nocodb/src/db/BaseModelSqlv2/group-by.ts:applyIeeeNanRank` (:100–:122; call sites :696, :710–:717).
**Signature:** rank key = `knex.raw("(?? <> 'NaN'::double precision)", [builder])` (cell) / `raw("??.?? <> 'NaN'::double precision", ['g', getAs(column)])` (group); gate = `baseModel.isPg && parsedTree?.dataType === NUMERIC`.
**Data Shape:** primary ORDER BY stays on the raw value with its existing NULLS FIRST/LAST contract; the boolean rank key rides the SAME direction as the value sort.

### Decisive source
```ts
// pg orders NaN above every number, including Infinity. Rank it below
// -Infinity instead: the flag is false only for NaN, so ascending puts
// that block first and descending puts it last.
qb.orderBy(knex.raw(`(?? <> 'NaN'::double precision)`, [builder]) as any,
           direction, nulls);
qb.orderBy(builder, direction, nulls);
```

**Flow:** cell sort: emit `(expr <> 'NaN')` FIRST with same direction+nulls, then the value expr — false(0)=NaN sorts before true values asc. Group sort: applyIeeeNanRank fires at BOTH call sites — count-direction branch (:696, hard-coded 'FIRST' so the NaN block leads asc) and plain asc/desc branch (:710, nulls chosen desc→LAST / asc→FIRST mirroring pg's NULLS convention) — always BEFORE the raw `g.<alias>` value ordering.
**Invariant:** (1) The group list and its contents must place NaN on the SAME side — without the group-side rank, keys sorted by raw value put the NaN group last while FormulaGeneralHandler.applySort puts its rows first. (2) Rank key is a BOOLEAN expression, so it composes with any direction without CASE materialization. (3) Filter side uses stripNaNSql for gt/lt/gte/lte only (`ORDERING_COMPARISON_OPS` :24) because eq/neq compare displayed tokens and MUST match 'NaN'; ±Infinity still compare normally. (4) Non-finite filter VALUES bind as `?::double precision` (numeric can't hold Infinity pre-pg14) and verify() admits them `{isValid:true}` BEFORE the Decimal verifier's numeric check 422s `eq NaN` (:175–:186).
**Probe:** `grep -n "ORDERING_COMPARISON_OPS =" …formula.general.handler.ts` → :24; `grep -c "applyIeeeNanRank" …group-by.ts` → 3 (def + 2 call sites). No upstream unit suite (caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "applyIeeeNanRank group-by formula sort NaN", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the boolean-rank-key pattern + two-sided agreement invariant; adapt which dialects need it; omit MSSQL NULLS replication (already mined in groupby-nulls-sort-contract).
