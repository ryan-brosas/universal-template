<!-- capsule-v2 -->
# pg-meta routine mutation plane — how do trigger and function DDL builders handle enable modes, rename ordering, saved-signature reuse, and config-param grammar?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** Triggers and functions are the two pg-meta entities whose mutations need more than pass-5's tables/columns/publications patterns — trigger state lives on the TABLE, function identity is its argument list, and function bodies carry a SET-parameter grammar. How do the builders encode those Postgres realities without opening injection channels?

## Trigger create: every slot through its escaper, condition as a branded fragment (`packages/pg-meta/src/pg-meta-triggers.ts`)
**Path/Symbol:** `packages/pg-meta/src/pg-meta-triggers.ts` : `PGTriggerCreate` (:105-127), `create` (:133-165), `update` (:167-200), `remove` (:202-211).
**Signature:** `create(params: PGTriggerCreate): { sql: SafeSqlFragment; zod: z.ZodType<void> }`; `update(id: { name, schema, table }, params: PGTriggerUpdate): { sql, zod }`.
**Data Shape:** names/tables/functions route through ident(), activation/events/orientation through keyword() (closed allowlist), function_args through literal(); `condition` is typed `SafeSqlFragment` — zod validates the runtime string but the BRAND is a separate compile-time trust check.

### Decisive source
```ts
// Zod validates `condition` as a runtime string; the SafeSqlFragment brand is a
// separate compile-time trust check. A parsed string is not automatically safe —
// callers must promote untrusted input via acceptUntrustedSql/rawSql before it can
// satisfy this type.
export type PGTriggerCreate = Omit<z.infer<typeof pgTriggerCreateZod>, 'condition'> & {
  condition?: SafeSqlFragment
}
```

**Flow:** create assembles `create trigger <ident> <keyword activation> <events joined ' or '> on <qualified table> [for each <orientation>] [when (<condition>)] execute function <qualified fn>(<literal args>);`.
**Invariant:** schema validation and SQL trust are ORTHOGONAL checks — a zod-parsed string is still untrusted SQL; only the brand check admits it. Never collapse the two.
**Probe:** `packages/pg-meta/test/triggers.test.ts` (DB-backed, read whole; standing runner block) pins the full create→list→retrieve-by-name/by-id→update→remove round-trip including a `when (old.* IS DISTINCT FROM new.*)` condition and lowercase event input round-tripping as uppercase catalog values.

## Trigger update: state lives on the table, rename last (`packages/pg-meta/src/pg-meta-triggers.ts`)
**Path/Symbol:** same file : `update` (:167-200).
**Signature:** `update(id: { name: string; schema: string; table: string }, params: PGTriggerUpdate)`.
**Data Shape:** enabled_mode ORIGIN/DISABLED/REPLICA/ALWAYS compiles to `alter table <t> enable|disable [replica|always] trigger <name>` — Postgres has no `alter trigger ... enable`; trigger state is per-table. Rename is skipped when new == old; both statements ride in one begin/commit.

### Decisive source
```ts
  // updateNameSql must be last
  const sql = safeSql`begin; ${enabledModeSql}; ${updateNameSql}; commit;`
```

**Flow:** enable-mode statement (or empty) → rename statement (or empty) → commit.
**Invariant:** map each mutation to the statement Postgres actually supports (enable/disable are ALTER TABLE operations), and keep rename LAST within the transaction — the same pinned ordering discipline as pass-5's tables/columns builders (rename after everything that references the old name).
**Probe:** triggers.test.ts pins rename+DISABLED in one update and a follow-up REPLICA update, verifying catalog state after each.

## Function saved-signature reuse: trust re-branded at the boundary (`packages/pg-meta/src/pg-meta-functions.ts`)
**Path/Symbol:** `packages/pg-meta/src/pg-meta-functions.ts` : `PGSavedFunction` (:214-222), `splitArgumentTypes` (:321-323), `update` (:326-382), `remove` (:393-401); test-side `asSavedFunction` (`test/functions.test.ts` :10).
**Signature:** `update(currentFunc: PGSavedFunction, { name?, schema?, definition? }): { sql, zod }`; `remove(func: PGSavedFunction, { cascade? })`.
**Data Shape:** update/remove take a PREVIOUSLY-FETCHED function whose wire-returned SQL strings (`argument_types`, `identity_argument_types`, `return_type`, `config_params` values) have been re-branded SafeSqlFragment at the API/database boundary — the round-trip twin of pass-3's query-cell source rebrand: trust flows database → wire → back into DDL, and the type system forces the promotion to be explicit.

### Decisive source
```ts
// `update()` and `remove()` reuse signature pieces from a previously-fetched
// function. Callers must pass a value whose raw-SQL fields (`argument_types`,
// `identity_argument_types`, `return_type`, and `config_params` values)
// have been branded at the API/database boundary.
export type PGSavedFunction = Omit<
  PGFunction,
  'argument_types' | 'identity_argument_types' | 'return_type' | 'config_params'
> & {
  argument_types: SafeSqlFragment
  identity_argument_types: SafeSqlFragment
  return_type: SafeSqlFragment
  config_params: Record<string, SafeSqlFragment> | null
}
```

**Flow:** fetch function (wire returns plain strings) → boundary re-brands the SQL-bearing fields → update/remove interpolate the branded signature into ALTER/DROP statements.
**Invariant:** values that CAME FROM the database may flow back into DDL, but only through an explicit, type-forced re-branding step at the boundary — never by implicit widening of wire strings into SQL positions.
**Probe:** functions.test.ts (:10) defines `asSavedFunction = fn as unknown as PGSavedFunction` — the test itself stands in for the boundary promotion; the DB-backed suite (:196, :258) exercises rename+schema-move+definition-change and remove through it (standing runner block).

## Function update: DO $$ guard with optimistic-concurrency check (`packages/pg-meta/src/pg-meta-functions.ts`)
**Path/Symbol:** same file : `update` (:326-382).
**Signature:** as above.
**Data Shape:** the whole mutation is one DO $$ plpgsql block: CREATE OR REPLACE only when a definition was passed (IF TRUE/FALSE), then a guard re-resolves the function by (schema, name, identity_argument_types) and RAISEs if the resolved id differs from the saved id; rename uses the FULL identity signature (Postgres identifies overloads by argument list); SET SCHEMA uses `name || currentFunc.name` so a same-statement rename+move targets the NEW name.

### Decisive source
```ts
        IF (
          SELECT id
          FROM (${FUNCTIONS_SQL}) AS f
          WHERE f.schema = ${literal(currentFunc.schema)}
          AND f.name = ${literal(currentFunc.name)}
          AND f.identity_argument_types = ${literal(identityArgs)}
        ) != ${literal(currentFunc.id)} THEN
          RAISE EXCEPTION ${literal(`Cannot find function "${currentFunc.schema}"."${currentFunc.name}"(${identityArgs})`)};
        END IF;
```

**Flow:** conditional replace → identity guard → rename → schema move, all inside one DO block.
**Invariant:** a mutation built from a SAVED snapshot must verify the live object still matches that snapshot before acting — the rename/replace refuses to fire if the function changed underneath (optimistic concurrency inside the same transaction). Overload-sensitive operations must carry the full argument signature, not just the name.
**Probe:** functions.test.ts retrieve-by-signature test (`p.proargtypes::text = <args>` in retrieve, :150-157) pins that function identity IS the argument list.

## config_params SET grammar: qualifiedIdent, FROM CURRENT sentinel, empty-string case (`packages/pg-meta/src/pg-meta-functions.ts`)
**Path/Symbol:** same file : `qualifiedIdent` (:223-237), `_generateCreateFunctionSql` (:240-283), `PGFunctionCreate` type comment (:188-207).
**Signature:** `qualifiedIdent(value: string): SafeSqlFragment`.
**Data Shape:** param NAME: neither keyword (regex rejects `.`) nor ident (would quote `"app.jwt_secret"` as ONE identifier, which Postgres reads as a single literal name) — split on `.`, ident each segment, rejoin with a literal `.`. Param VALUE: `'FROM CURRENT'` (string-equality sentinel) → `SET <param> FROM CURRENT`; `'""'` → `literal('')`; otherwise the branded fragment interpolates raw after `SET <param> TO`.

### Decisive source
```ts
function qualifiedIdent(value: string): SafeSqlFragment {
  return value
    .split('.')
    .map(ident)
    .reduce<SafeSqlFragment>(
      (acc, part, i) => (i === 0 ? part : safeSql`${acc}.${part}`),
      safeSql``
    )
}
```
```ts
          Object.entries(config_params).map(([param, value]) =>
            value === 'FROM CURRENT'
              ? safeSql`SET ${qualifiedIdent(param)} FROM CURRENT`
              : safeSql`SET ${qualifiedIdent(param)} TO ${value === '""' ? literal('') : value}`
          ),
```

**Flow:** create/update builds the SET ladder from config_params; procedures omit RETURNS/behavior/strictness (isProcedure ternaries); the definition body goes through literal() so it is dollar-quote-safe.
**Invariant:** namespaced custom GUCs (`app.jwt_secret`, `pgaudit.log`) need per-segment identifier quoting — whole-value quoting changes the meaning; grammar sentinels ('FROM CURRENT', '""') must be exact string matches documented at the type, and every other value must arrive branded.
**Probe:** functions.test.ts pins all three value shapes end-to-end: `create function with various config_params values` (:314, FROM CURRENT reads back as the session value), `update function with empty string search_path` (:352, `'""'` survives update), `create function with namespaced custom GUC config_params` (:385, `app.jwt_secret` round-trips). DB-backed; standing runner block.

## Indexes: the read-only counter-example (`packages/pg-meta/src/pg-meta-indexes.ts`)
**Path/Symbol:** `packages/pg-meta/src/pg-meta-indexes.ts` (105L whole) : `list` (:41-89), `retrieve` (:91-103).
**Signature:** `list({ includeSystemSchemas?, includedSchemas?, excludedSchemas?, limit?, offset? }): { sql, zod }`.
**Data Shape:** same filterByList/limit/offset ladder as every entity module — but NO create/update/remove exists: indexes are managed by table DDL, not by their own mutation plane.
**Invariant:** a mutation plane exists only where Postgres grants one; do not invent builders for entities Postgres only exposes read-only.
**Probe:** direct read at the pin; module verified to export list/retrieve only.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads at the pin (every cited file additionally md5-verified byte-identical to its HEAD blob). Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "PGSavedFunction qualifiedIdent pgTriggerCreate updateNameSql enabled_mode config_params FROM CURRENT", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: orthogonal zod-validation vs SQL-brand checks; statement mapping to what Postgres actually supports (trigger state via ALTER TABLE); rename-last ordering inside one transaction; saved-signature reuse with boundary re-branding; DO $$ optimistic-concurrency guards; per-segment qualified-ident for namespaced GUCs; exact-match grammar sentinels; RESTRICT-default drops with full identity signatures; read-only modules stay read-only. Adapt the escaper names and zod schemas to your host. Omit Supabase-product specifics: the FUNCTIONS_SQL/TRIGGERS_SQL catalog views and the studio API boundary that performs the re-branding. Direct-test caveat: triggers.test.ts and functions.test.ts are DB-backed suites read whole under the standing runner block (vitest unexecutable in-lane, never claimed passing); no pure unit tests exist for these builders.
