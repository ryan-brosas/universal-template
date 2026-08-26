<!-- capsule-v2 -->
# Field-to-field LIKE refs — how does a dynamic filter compare a column AGAINST another column without stringifying it?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When filter.value is a knex raw/ref (dynamic field-to-field filter), how do wildcards get concatenated per dialect?

## ncIsKnexRawOrRef + ncLikePatternForRef
**Path/Symbol:** `packages/nocodb/src/db/field-handler/utils/handlerUtils.ts` — `ncIsStringHasValue` (:30-32), `ncIsKnexRawOrRef` (:39-43), `ncLikePatternForRef` (:53-63).
**Signature:** `ncLikePatternForRef(knex: CustomKnex, ref: Knex.Raw): Knex.Raw` — returns a raw SQL fragment, never a string.
**Data Shape:** Detection is structural: `!!val && typeof val === 'object' && val.isRawInstance === true`.

### Decisive source
```ts
// :45-52 — the trap this prevents:
// The wildcards must be concatenated in SQL — dialect specific — so the
// reference stays a reference. Interpolating it in JS (`%${ref}%`)
// stringifies the reference into a literal, which never matches.
if (client === 'mysql' || client === 'mysql2' || client === 'vitess') {
  return knex.raw("CONCAT('%', ?, '%')", [ref]);
}
if (client === 'mssql') {
  return knex.raw("('%' + ? + '%')", [ref]);
}
// pg, sqlite3, oracledb, databricks and default support `||` concatenation
return knex.raw("('%' || ? || '%')", [ref]);
```

**Flow:** generic filterLike/filterNlike check `ncIsKnexRawOrRef(val)` FIRST — ref path builds the dialect pattern and compares (Oracle wraps both sides in UPPER because its LIKE is case-sensitive while pg→ilike/MySQL-collation are CI); scalar path keeps the classic `%val%` literal form.
**Invariant:** (1) The ref must ride as a BINDING (`?`) inside the pattern raw, not be inlined — that's what keeps it a column reference. (2) mssql uses `+` string concat (no CONCAT n-ary guarantee pre-2012 compat), Oracle gets UPPER-wrapping for parity. (3) Empty-value handling still follows the scalar branch semantics even when detection fails — order of checks matters.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep `isRawInstance === true` sole definition site; search_graph resolves `ncLikePatternForRef Function ... handlerUtils.ts 53-63` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "ncLikePatternForRef", limit: 5 });
```

## Verdict
Adopt the three-way dialect concat table and the isRawInstance duck-check; adapt client names to your driver; omit nothing. Caveat: no direct tests at pin.
