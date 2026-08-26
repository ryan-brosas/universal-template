<!-- capsule-v2 -->
# SQL diagnostics collector — how do you fingerprint SQL for analytics with samples OFF by default?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How are SQL statements captured into bounded, literal-free diagnostics attached to an execution context?

## Context-slot collector with save/restore nesting
**Path/Symbol:** `packages/v2/table-query-ops/src/sqlDiagnostics.ts` whole (106L): key `TABLE_QUERY_SQL_DIAGNOSTICS_CONTEXT_KEY = Symbol.for('teable.v2.tableOps.sqlDiagnostics')` (:5-7), config (:9-19: `captureSqlSample:false, maxSampleLength:2000, maxDiagnosticsPerObservation:4`), `createTableQuerySqlDiagnosticsCollector` (:36-70), `attachTableQuerySqlDiagnosticsCollector` (:72-94), `normalizeSql` (:96-101), `statementKind` (:103), `truncateSql` (:105-106).
**Signature:** `attach(context, config?) → {collector: {record({source, sql, parameters?}), snapshot()}, restore()}`.
**Data Shape:** diagnostic = `{source, statementKind (first word lowercased), fingerprint (stableHash of normalized SQL), parameterCount, sampled:boolean, normalizedSql?:≤4000 chars}`; observation schema caps the array at 8.

### Decisive source
```ts
attach(context, config?) {
  const previous = context[KEY];                 // save outer collector (nesting-safe)
  const collector = createTableQuerySqlDiagnosticsCollector(config);
  context[KEY] = collector;
  return { collector,
    restore() {
      if (previous) context[KEY] = previous;     // hand back to outer scope
      else delete context[KEY];                  // clean slate — no stale leakage
    } };
}
record(input) {
  if (diagnostics.length >= resolved.maxDiagnosticsPerObservation) return;  // bounded
  const normalizedSql = normalizeSql(input.sql); // strip --/-- comments + /*…*/ + collapse ws
  if (!normalizedSql) return;
  …fingerprint: stableHash(normalizedSql), parameterCount, sampled: captureSqlSample…
}
```

**Flow:** decorator attaches per-query → downstream driver layers read the SAME context slot and call record() for each statement → snapshot rides on the observation window → restore unwinds. Samples (`normalizedSql` payload itself) exist ONLY when `captureSqlSample:true`; default captures fingerprints + parameter counts exclusively.
**Invariant:** Fingerprints derive from normalized SQL so identical shapes dedupe regardless of formatting/parameters; cap-first means a hot query emits at most N diagnostics per window (first-come, not worst-case); Symbol.for global registry lets unrelated modules share the slot without import cycles. Note the sibling primitive in `adapter-db-postgres-shared/src/PostgresSqlExecutionError.ts`: same redact-normalize idea but FNV-1a-64 fingerprint + error-position-windowed sample + `parametersCaptured:false` typed guarantee — use that one for ERROR paths, this one for observation.
**Probe:** `sqlDiagnostics.spec.ts:8` "records SQL fingerprints without SQL samples by default"; :29 "records normalized SQL samples only when enabled".
**Coverage caveat:** none — both modes directly tested.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "attachTableQuerySqlDiagnosticsCollector normalizeSql stableHash", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt save/restore context-slot collection and fingerprint-without-sample defaults; adapt caps; keep the two-collector split (observation vs error) — merging them loses either the position window or the cheap default.
