<!-- capsule-v2 -->
# ident() fe-exec port — when does an identifier stay bare and how are the rest quoted?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** Which identifiers may appear unquoted in generated SQL, and what exact ladder handles booleans, dates, arrays, and hostile strings?

## Identifier escaping ladder
**Path/Symbol:** `packages/pg-meta/src/pg-format/index.ts` : `ident` (:93-134), `isReserved` (:68-73).
**Signature:** `export function ident(value?: unknown): SafeSqlFragment`.
**Data Shape:** accepts any JS value; returns branded identifier text. Throws `Error` for null/undefined/objects and nested arrays; `TypeError` for a nested array element. Ported from PostgreSQL 9.2.4 `src/interfaces/libpq/fe-exec.c`.

### Decisive source
```ts
const tident = String(value).slice(0) // create copy

// do not quote a valid, unquoted identifier
if (/^[_a-z][\d$_a-z]*$/.test(tident) === true && isReserved(tident) === false) {
  return tident as SafeSqlFragment
}

let quoted = '"'
for (const c of tident) {
  quoted += c === '"' ? c + c : c
}
quoted += '"'
return quoted as SafeSqlFragment
```

**Flow:** null/undefined → throw · `false`/`true` → `"f"`/`"t"` · Date → `"ISO-8601 with T→space, Z→+00"` · array → one-level flatten, each element recursed, joined with `,` (nested array → TypeError; note: joined WITHOUT quotes around the group) · object (`value === Object(value)`) → throw · lowercase-safe fast path → bare token · else → double-quoted with inner `"` doubled.
**Invariant:** the fast path requires BOTH the strict lowercase regex AND non-reserved membership in `POSTGRESQL_RESERVED_WORDS` — `camelCaseColumn` and `collation` must both be quoted. Quote-doubling is the only escaping inside quotes (no backslash handling needed for identifiers in PG).
**Probe:** `packages/pg-meta/test/pg-format.test.ts` describe `'ident'` — `ident('collation') === '"collation"'`, `ident('camelCaseColumn') === '"camelCaseColumn"'`, `ident('column$with$dollar') === 'column$with$dollar'` ($ allowed unquoted), `ident('quoted"column') === '"quoted""column"'`, throws on null/nested-array/object.
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "pg-format unit test escaping identifier literal E-string backslash doubling", limit: 25 })
// ident :93-134 rank 7; literal :138-213 rank 1 — decisive pair surfaced line-exact
```

## Verdict
Adopt the fast-path regex + reserved-word gate + quote doubling verbatim; it is battle-tested libpq behavior. Adapt `POSTGRESQL_RESERVED_WORDS` sourcing (pg-meta vendors it in `pg-format/reserved`). Omit nothing from the throw-ladder: silently coercing null→'' or accepting objects is exactly the bug class this function exists to prevent.
