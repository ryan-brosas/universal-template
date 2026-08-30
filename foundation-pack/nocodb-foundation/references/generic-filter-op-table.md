<!-- capsule-v2 -->
# Generic filter op table — what exact SQL does every comparison op emit, and where do the ''-vs-NULL gates live?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do blank/notblank/empty/notempty/null/notnull differ per column type and dialect, and how are negations kept NULL-correct?

## GenericFieldHandler filter ops
**Path/Symbol:** `packages/nocodb/src/db/field-handler/handlers/generic.ts` — dispatch switch :126-229; eq :243; neq :272; like :331; nlike :381; blank :453; null/notnull :497/:522; empty :550; notempty :575; notblank :608; is/isnot :646/:691; btw/nbtw :827/:845; allof-family :900-985 (methods :928-985).
**Signature:** each `filterOp(args: {sourceField, val}, rootArgs: {knex, filter, column}, options): Promise<FilterOperationResult>` — always `{rootApply: undefined, clause}` for this class; bound via `.bind(this)` at :232 to survive method-table dispatch.
**Data Shape:** Gates: `isEmptyStringIncompatible(uidt)` = numeric ∪ {Date, DateTime, CreatedTime, LastModifiedTime, Time, Checkbox} (:30-39); `emptyStringIsNull(knex)` = clientType 'oracledb' (:46-47); `isNativePgEnum` = `column.internal_meta.pg_enum_type_name`.

### Decisive source
```ts
// :26-29 — why the type gate exists:
// Empty-string comparisons (`= ''` / `!= ''`) only make sense for text-like
// columns. Numeric / date / time columns can't be compared to '' — PG raises
// a cast error — so `blank`/`notblank` reduce to IS NULL / IS NOT NULL.
// :41-45 — the Oracle arm:
// Oracle has no empty-string value — '' IS NULL there — so `= ''` / `!= ''`
// terms degenerate into NULL comparisons (never true) and would flip the
// meaning of blank/notblank-style clauses.
```

**Flow:** neq with a value emits `?? != ? OR WHERE NULL` (negation re-admits NULL); nlike appends `%${val}%` unless val already has wildcards, then adds `OR field='' OR NULL` (or only NULL when val==='%%'); notempty on Oracle short-circuits to literal `1 = 1` because excluding '' excludes nothing (`col <> NULL` never true, so the naive shape would match only NULL rows); is/isnot route by keyword value (blank→filterBlank, null→strict whereNull...) making them complements of each other; btw/nbtw split `"lower,upper"` strings (these had NO case after the conditionV2 migration and fell through to unsupportedFilter — now restored).
**Invariant:** (1) Three-way split null/empty/blank is deliberate parity restoration — collapsing them "made null/empty/blank behave identically and broke the filter parity tests" (field-handler.interface.ts docstring). (2) Every negation op must re-admit NULL or silent row loss. (3) Oracle arms emit `1 = 1`, never SQL `TRUE` (no boolean literal pre-23ai). (4) allof/nanyof share innerFilterAllAnyOf: items matched against `,${col},` and `, ${col},` (space variant) via CONCAT wrap; negated forms use whereNot(condition)+orWhereNull; PG overrides swap like→ilike + ::text casts.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep the :26-45 gate comments; search_graph resolves `GenericFieldHandler.filterEq ... generic.ts 243-270` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "GenericFieldHandler filterBlank", limit: 10 });
```

## Verdict
Adopt the op→SQL table verbatim including the three-gate matrix (type × dialect × pg-enum); adapt binding style; omit nothing — every branch encodes a real dialect incident. Caveat: no direct tests at pin.
