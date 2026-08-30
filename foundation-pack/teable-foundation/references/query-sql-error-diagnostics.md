<!-- capsule-v2 -->
# SQL execution error diagnostics — how do you turn a driver error into a redacted, fingerprinted diagnostic without losing the cause?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is a failed Postgres statement wrapped so logs carry SQLSTATE, error position, and a literal-free SQL window — never parameters?

## FNV-1a-64 fingerprint + position-windowed sample + typed no-parameters
**Path/Symbol:** `packages/v2/adapter-db-postgres-shared/src/PostgresSqlExecutionError.ts` whole (160L): `PostgresSqlExecutionError` (:117-155), `redactSqlLiterals` (:65-70), `fingerprint` (:72-79), `buildSqlSample` (:83-98), `buildPostgresFields` (:100-115), `getPostgresSqlExecutionDiagnostics` (:157-160).
**Signature:** `new PostgresSqlExecutionError(cause: unknown, compiled: Pick<CompiledQuery,'sql'|'parameters'>, context: PostgresSqlExecutionContext)`; MAX_SQL_SAMPLE_LENGTH=4000.
**Data Shape:** `diagnostics.version:1` envelope = `{source, statement:{kind,fingerprint:`fnv1a64:<16hex>`,sqlLength,parameterCount,parametersCaptured:false,normalizedSql,sampleStart,truncated}, postgres?:{sqlState,severity,position,routine,schema,table,column,dataType,constraint}, context?:{tableId,tableName,fieldIds,stepLevel}}`.

### Decisive source
```ts
const redactSqlLiterals = (sql: string): string =>
  sql.replace(/'(?:''|[^'])*'/g, "'<literal>'")     // escaped-quote-aware string literals
     .replace(/\b\d+(?:\.\d+)?\b/g, '<number>')
     .replace(/\s+/g, ' ').trim();

const buildSqlSample = (sql, errorPosition?) => {
  const zeroBased = errorPosition == null ? 0 : Math.max(0, errorPosition - 1);
  const sampleStart = Math.max(0, Math.min(sql.length - 4000, zeroBased - 2000)); // center window on PG position
  …truncated: sampleStart > 0 || sample.length < sql.length…
};
this.name = cause instanceof Error ? cause.name : 'PostgresSqlExecutionError';  // driver class preserved
```

**Flow:** catch driver throw → wrap with compiled query + call-site context → extract Postgres fields ONLY from known string/number props (empty ⇒ omit the whole postgres block) → sample centered on `error.position` (PG reports 1-based) → literals redacted AFTER windowing → accessor returns diagnostics only for the wrapper type.
**Invariant:** Parameters are NEVER captured (`parametersCaptured:false` is a compile-time-checked literal); the original cause rides via `super(message,{cause})` and the error NAME mirrors the driver's so existing instanceof checks keep working; version field future-proofs log parsers. Contrast with table-query-ops sqlDiagnostics: this one exists for ERROR paths (position windows, SQLSTATE), that one for observation (cheap stableHash).
**Probe:** no dedicated spec file at this HEAD — pure module verified by source reading; parse_partial flag covers line 160 only. Coverage caveat recorded.
**Coverage caveat:** no direct test upstream; contract pinned by source + type-level guarantees.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresSqlExecutionError redactSqlLiterals buildSqlSample fnv1a64", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt quote-aware literal redaction, position-centered samples, and the parametersCaptured:false guarantee wholesale; adapt the context block; keep the cause-preserving name passthrough.
