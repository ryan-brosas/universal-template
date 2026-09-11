<!-- capsule-v2 -->
# literal() escaping ladder — how does any JS value become an injection-proof SQL literal?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What is the full value-type → SQL-literal mapping, and why do backslashes force an `E''` prefix?

## Literal rendering ladder
**Path/Symbol:** `packages/pg-meta/src/pg-format/index.ts` : `literal` (:138-213), helper `formatDate` (:64-66), `arrayToList` (:75-89).
**Signature:** `export function literal(value?: unknown): SafeSqlFragment`.
**Data Shape:** any JS value → branded literal text. Order matters: special number cases must be tested BEFORE the generic `typeof value === 'number'` branch (in-source comment).

### Decisive source
```ts
if (value === undefined || value === null) return 'NULL' as SafeSqlFragment
if (typeof value === 'bigint') return BigInt(value).toString() as SafeSqlFragment
if (value === Number.POSITIVE_INFINITY) return "'Infinity'" as SafeSqlFragment
// ... NEGATIVE_INFINITY, NaN ...
if (typeof value === 'number') return Number(value).toString() as SafeSqlFragment
// booleans -> 't' / 'f'; Date -> 'ISO...'; arrays recurse; objects:
if (value === Object(value)) {
  explicitCast = 'jsonb'
  tliteral = JSON.stringify(value)
}
let hasBackslash = false
let quoted = "'"
for (const c of tliteral) {
  if (c === "'") quoted += c + c
  else if (c === '\\') { quoted += c + c; hasBackslash = true }
  else quoted += c
}
quoted += "'"
if (hasBackslash === true) quoted = `E${quoted}`
if (explicitCast) quoted += `::${explicitCast}`
```

**Flow:** NULL · bigint · ±Infinity/NaN specials · plain number · `'t'/'f'` · quoted ISO date (T→space, Z→+00) · array recursion (nested rows become `(a,b)` groups via arrayToList, first group without leading space) · object → `'json'::jsonb` · string body with `'` AND `\` both doubled, `E` prefix when any backslash was seen.
**Invariant:** the `E''` prefix is not cosmetic: in standard-conforming strings a bare `\` is literal, but doubling without the escape prefix would change content under `standard_conforming_strings=off`; flagging backslashes and switching to explicit-escape syntax keeps both modes correct. Objects MUST carry `::jsonb`, not `::json`.
**Probe:** `packages/pg-meta/test/pg-format.test.ts` describe `'literal'` — `literal('path\\to\\file') === "E'path\\\\to\\\\file'"`, `literal({name:'test'}) === '\'{"name":"test"}\'::jsonb'`, `literal(BigInt('9007199254740991'))` exact digits (no float mangling), `literal(new Date('2024-01-01T00:00:00Z')) === "'2024-01-01 00:00:00.000+00'"`.
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "pg-format unit test escaping identifier literal E-string backslash doubling", limit: 25 })
// literal :138-213 rank 1, safeSql :359-367 rank 12 — whole kernel co-ranked line-exact
```

## Verdict
Adopt the whole ladder including branch ORDER (NaN/Infinity before generic number) and the E-prefix flag. Adapt the Date projection if your host needs timestamptz precision beyond ISO milliseconds. Omit the `::jsonb` cast only by replacing it with your host's equivalent binary-json cast — never emit raw JSON as a string literal.
