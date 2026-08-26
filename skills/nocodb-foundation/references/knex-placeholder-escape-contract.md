<!-- capsule-v2 -->
|# knex-client placeholder escaping — how do raw SQL fragments carry `?`/`??` through repeated toQuery() materializations without being eaten as bind slots?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the exact sanitize/unsanitize/genQuery contract, and when must a caller re-escape?

## knex-client placeholder escaping
**Path/Symbol:** `packages/nocodb/src/db/sql-client/lib/KnexClient.ts:genQuery` (:1865–1873), `sanitize` (:1875–1879), `unsanitize` (:1881–1883), `genValue`/`genIdentifier`/`genRaw` (:1885–1899), `sanitiseDataType` (:1901–1907).
**Signature:** `sanitize(str)` escapes EVERY `?` run not preceded by a backslash; `unsanitize(str)` collapses `\?` back; `genQuery(query, args=[], shouldSanitize=0)` binds args into knex.raw then (if sanitizing) sanitizes BOTH the interpolated args and the final string.
**Data Shape:** `?` = value bind, `??` = identifier bind (knex); `\?` = literal question mark in emitted SQL.

### Decisive source
```ts
// :1875–1879 — the regex is the whole contract:
sanitize(str) {
  return str.replace(/([^\\]|^)(\?+)/g, (_, m1, m2) =>
    `${m1}${m2.split('?').join('\\?')}`);
}
// :1865–1873 — composition order matters:
genQuery(query, args = [], shouldSanitize = 0) {
  if (shouldSanitize)
    args = (Array.isArray(args)?args:[args]).map(s => typeof s==='string'?this.sanitize(s):s);
  const rawQuery = this.sqlClient.raw(query, args).toQuery();   // knex CONSUMES ? / ?? here
  return shouldSanitize ? this.sanitize(rawQuery) : this.unsanitize(rawQuery);
}
```
Downstream double-materialization sites that MUST re-escape on exit (all verified at pin): PgClient generic assembler `knex.raw(\`${calleeName}(${callArgs})\`.replace(/\?/g,'\\?'))`; MysqlClient tableUpdate wraps accumulated fragments `genQuery(\`ALTER TABLE ?? ${this.sanitize(upQuery)};\`,[tn])`; SqliteClient alterTableColumn builds four statements with shouldSanitize=true then concatenates them for splitQueries.

**Flow:** build fragment with placeholders + args → `sqlClient.raw(...).toQuery()` consumes real binds → if the RESULT string will be fed to another raw()/toQuery() round, it must be sanitized on the way out so its embedded `?` survive the next pass. genRaw strips the outer quotes knex adds around a bound value (`q.substring(1,q.length-1)`) — but only for non-number/non-boolean inputs.

**Invariant:** (1) Escape state is per-materialization, not global: a fragment that already went through toQuery() once holds LITERAL `?` characters only if someone sanitized it — forgetting the flag silently turns them into bind slots of the NEXT query (bind-count mismatch or wrong-value injection). (2) The `([^\\]|^)` guard makes sanitize idempotent-ish (never double-escapes `\?`) but NOT commutative with unsanitize ordering errors — unsanitizing a never-bound template deletes meaningful escapes. (3) genValue/genIdentifier always sanitize; plain genQuery defaults to UNSANITIZED — callers opt in per call site, which is exactly where porters slip. (4) `sanitiseDataType` allowlists `/^[\w -]+(\(\d+(,\d+)?\))?$/` before any type string enters SQL.

**Probe:** runner BLOCKED (no upstream unit tests import KnexClient — grep across src/**/*.spec.ts = 0 hits) → deterministic probes executed at pin: `sed -n '1875,1883p' packages/nocodb/src/db/sql-client/lib/KnexClient.ts` shows both functions byte-exact; `grep -c "shouldSanitize" packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts` = 20+ (opt-in density); `grep -c 'replace(/\\\\?/g' packages/nocodb/src/db/formulav2/parsed-tree-builder.ts` ≥1 (the sibling plane's exit re-escape).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "KnexClient genQuery sanitize unsanitize genValue", limit: 10 });
```

## Verdict
Adopt the escape-on-exit discipline (any composed-then-rematerialized SQL string must be sanitized at each boundary) and the typed allowlist for data-type strings; adapt the marker syntax if the host ORM uses different bind tokens; omit genRaw's quote-stripping unless you also port knex's value serialization.
