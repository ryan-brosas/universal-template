<!-- capsule-v2 -->
# withArray/format specifier engine — how do %1$s positional specifiers mix with sequential ones?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What are the exact semantics of `%s/%I/%L`, `%n$` positions, and reusing an argument in a format string?

## Format-specifier replacement engine
**Path/Symbol:** `packages/pg-meta/src/pg-format/index.ts` : `withArray` (:303-348), `format` (:350-352), `config` (:284-301), `FMT_PATTERN_CONFIG` (:57-61).
**Signature:** `export function withArray(fmt: SafeSqlFragment, parameters: SafeSqlFragment[]): SafeSqlFragment`; `export function format(fmt: SafeSqlFragment, ...arguments_: SafeSqlFragment[]): SafeSqlFragment`.
**Data Shape:** fmt carries `%I`(ident) `%L`(literal) `%s`(raw stringify) `%%`(percent) specifiers; `%2$s` style prefixes select position 1-based. The specifier letters themselves come from the mutable module config (default I/L/s).

### Decisive source
```ts
let position = index
const tokens = type.split('$')
if (tokens.length > 1) {
  position = Number.parseInt(tokens[0], 10) - 1
  type = tokens[1]
}
if (position < 0) throw new Error('specified argument 0 but arguments start at 1')
else if (position > parameters.length - 1) throw new Error('too few arguments')

index = position + 1   // <-- sequential cursor jumps to AFTER the last positional hit

if (type === FMT_PATTERN_CONFIG.ident) return ident(parameters[position])
if (type === FMT_PATTERN_CONFIG.literal) return literal(parameters[position])
if (type === FMT_PATTERN_CONFIG.string) return string(parameters[position])
```

**Flow:** regex rebuilt from config → global replace over fmt → `%%` emits a literal `%` · explicit `%n$X` reads parameter n−1 and ADVANCES the sequential cursor past n · subsequent bare `%X` continue from there · out-of-range or zero position throws.
**Invariant:** the cursor-advance rule is what lets one argument be reused (`insert into %1$s ... null::%1$s, %2$s`) while later bare specifiers still bind correctly — Query.utils' insert/update builders depend on exactly this. Specifier letters are config-driven, so any port that hardcodes I/L/s breaks `config()` consumers.
**Probe:** `packages/pg-meta/test/pg-format.test.ts` has no direct withArray cases (coverage caveat — behavior pinned indirectly by the DB-backed snapshot suite); decisive consumer anchor instead: `Query.utils.ts:87-98` builds `insert into %1$s (%2$s) select %2$s from jsonb_populate_recordset(null::%1$s, %3$s)` and relies on reuse + advance semantics. DB suite: `test/query/advanced-query.test.ts` (live-Postgres required).
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "safeSql untrustedSql acceptUntrustedSql branded sql format escape", limit: 40 })
// format :350-352 rank 6, withArray :303-348 rank 17 — engine co-ranked with kernel
```

## Verdict
Adopt the positional/sequential mixing arithmetic verbatim — it is subtle and load-bearing for argument-reuse templates. Adapt specifier letters through a config object if your host needs different letters; keep them mutable-at-module-scope ONLY if single-threaded per process. Omit `%s` from security-sensitive paths: it stringifies WITHOUT escaping, unlike `%I`/`%L`.
