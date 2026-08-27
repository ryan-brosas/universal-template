<!-- capsule-v2 -->
# Analytics SQL disjoint-brand kernel — why can't a Postgres-safe SQL brand be reused for BigQuery/ClickHouse queries, and what does the second brand family look like?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** A dashboard executes SQL against two dialect families (Postgres via pg-meta, BigQuery/ClickHouse for logs). How is the safe-SQL taint model (pass-2's sql-taint-brand-kernel) duplicated per dialect so a fragment escaped for one engine can never silently compose into the other?

## Disjoint brand decision (`data/logs/safe-analytics-sql.ts`)
**Path/Symbol:** `apps/studio/data/logs/safe-analytics-sql.ts` : header security-model comment (:1-33), `SafeLogSqlFragment` (:52), `UntrustedLogSqlFragment` (:65), `untrustedLogSql` (:73-75), `acceptUntrustedLogsSql` (:85-87), `safeSql` tag (:110-118), internal `rawSql` (:126-128), `joinSqlFragments` (:131-136).
**Signature:** `type SafeLogSqlFragment = string & { readonly __safeLogSqlFragmentBrand: never }`; `safeSql(strings: TemplateStringsArray, ...interpolated: Array<SafeLogSqlFragment>): SafeLogSqlFragment`.
**Data Shape:** the in-source rationale is the load-bearing part: pg-meta's `literal()` emits `E'…'` strings and `::jsonb` casts and its `ident()` double-quotes — all WRONG for BigQuery (double-quoted tokens are STRING LITERALS there) and ClickHouse. So the brands are intentionally distinct from pg-meta's: neither family can be promoted through the other's boundary nor composed into the other's queries. The promotion rule mirrors pass-2 exactly — `acceptUntrustedLogsSql` only inside a deliberate user-action event handler. One tightening vs pg-meta: `rawSql` is NOT exported; external callers must compose via `safeSql` + the sanitization helpers, never by casting arbitrary strings. `joinSqlFragments` takes a closed union of structural separators (`,`, `;\n`, ` and `, ` union all `, …) rather than an arbitrary string.

### Decisive source
```ts
// The brand `SafeLogSqlFragment` is intentionally distinct from pg-meta's
// `SafeSqlFragment`: escaping that is safe for Postgres (`E'…'` strings,
// `::jsonb` casts, double-quoted identifiers) is not safe for BigQuery or
// ClickHouse, and vice versa. Keeping the brands disjoint prevents a
// Postgres-escaped fragment from being composed into an analytics query
// (or vice versa) and silently emitting unsafe SQL.
export type SafeLogSqlFragment = string & { readonly __safeLogSqlFragmentBrand: never }

function rawSql(sql: string): SafeLogSqlFragment {   // NOT exported
  return sql as SafeLogSqlFragment
}
```

**Flow:** external text enters at the editor boundary as `untrustedLogSql` → user Run gesture promotes via `acceptUntrustedLogsSql` → values flow in only through `analyticsLiteral`/`quotedIdent`/`keyword` outputs or static `safeSql` template text → the wire boundary (`executeAnalyticsSql`) accepts only `SafeLogSqlFragment` at compile time.
**Invariant:** one brand family PER DIALECT. A shared "safe SQL" brand across engines is a silent-injection hole the moment escaping rules diverge (and they always do: quote style, escape prefixes, cast syntax, identifier quoting).
**Probe:** `apps/studio/data/logs/safe-analytics-sql.test.ts` (pure vitest, read whole; unexecutable in-lane — standing block) pins disjointness with `@ts-expect-error`: both pg-meta's untrusted AND promoted-safe brands are rejected at the logs boundary; plain strings and widened-to-string fragments are rejected at `executeAnalyticsSql`; promotion preserves text unchanged and composes via `safeSql`.

## Dialect-specific sanitizers
**Path/Symbol:** same file : `analyticsLiteral` (:138-158), `SAFE_IDENT_RE` (:160), `keyword` (:170-179), `quotedIdent` (:190-196).
**Signature:** `analyticsLiteral(value: string | number | boolean): SafeLogSqlFragment`; `keyword(value: string, allowed: readonly SafeLogSqlFragment[]): SafeLogSqlFragment`; `quotedIdent(value: string): SafeLogSqlFragment`.
**Data Shape:** literals — non-finite numbers THROW (no `Infinity`/`NaN` specials like pg-meta's literal ladder); booleans → bare `true`/`false`; strings double BOTH `'` and `\` inside plain `'…'` (the shared ClickHouse/BigQuery convention). Identifiers — backtick-quoted PER SEGMENT of a dotted path (`request.method` → `` `request`.`method` ``), strict `[A-Za-z_][A-Za-z0-9_]*` per segment, REJECT rather than escape (column names never need special characters; backticks are accepted by both engines). Keywords — case-insensitive match against a caller-supplied allow-list of pre-branded fragments, returning the ALLOWED fragment, never the raw input.

### Decisive source
```ts
export function analyticsLiteral(value: string | number | boolean): SafeLogSqlFragment {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw new Error('analyticsLiteral: non-finite numbers are not supported')
    }
    return rawSql(String(value))
  }
  // ...
  let escaped = ''
  for (const c of value) {
    if (c === "'") escaped += "''"
    else if (c === '\') escaped += '\\'
    else escaped += c
  }
  return rawSql(`'${escaped}'`)
}

export function quotedIdent(value: string): SafeLogSqlFragment {
  const segments = value.split('.')
  if (segments.length === 0 || segments.some((s) => !SAFE_IDENT_RE.test(s))) {
    throw new Error(`quotedIdent: invalid identifier "${value}"`)
  }
  return rawSql(segments.map((s) => '`' + s + '`').join('.'))
}
```

**Flow:** UI/URL/LLM-originated filter keys and values each pass their matching sanitizer before interpolation; operators go through `keyword(op, [safeSql\`AND\`, safeSql\`OR\`])` so the permitted set is known at compile time; dotted column paths go through `quotedIdent`.
**Invariant:** reject-don't-escape for identifiers (an allow-list regex with no escape path cannot regress); throw on non-finite numbers instead of emitting engine-specific spellings; keyword matching returns the canonical allowed fragment so casing can't drift.
**Probe:** same test file pins: `keyword('and', [AND, OR])` returns `'AND'` (allow-listed fragment, not raw input) and throws with the list in the message; `quotedIdent('request.method; DROP TABLE')` and `'a..b'` throw; `analyticsLiteral('hello')` composes to `"SELECT 'hello'"`; dotted paths backtick-quote every segment.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct whole-file reads plus the direct test at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "SafeLogSqlFragment analyticsLiteral quotedIdent acceptUntrustedLogsSql executeAnalyticsSql", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-dialect brand duplication wholesale — it is the single most portable lesson in this file: when you add a second SQL engine, copy the brand family, do not share it. Adopt reject-don't-escape identifiers, throw-on-non-finite literals, allow-list-keyword-canonicalization, and the unexported rawSql tightening. Adapt the separator union and sanitizer set to your engine pair's actual conventions. Omit nothing from the disjointness invariant; if your language lacks nominal branding, emulate with wrapper classes per dialect plus a cross-composition compile check (the @ts-expect-error tests are the porting checklist). Caveat: this kernel covers string/number/boolean only by design — objects have no analytics-literal form, which is itself a guard against accidental JSON splicing.
