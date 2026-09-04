<!-- capsule-v2 -->
# EXPLAIN-analyzer reuse of insert builders — how do read-only analyzers produce the exact write SQL without any write capability?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc5`; Codebase Memory `teable`. **Question:** How do the command-explain (EXPLAIN) analyzers consume RecordInsertBuilder, and what does that force the builder's API to guarantee?

## Analyzer-side construction
**Path/Symbol:** `packages/v2/command-explain/src/analyzers/CreateRecordAnalyzer.ts:186–187` and `packages/v2/command-explain/src/analyzers/PasteCommandAnalyzer.ts:426`.
**Signature:** `new RecordInsertBuilder(analyzer.db as unknown as Kysely<DynamicDB>)` then `builder.build({table, tableName, fieldValues, context})` — compiled SQL returned, NEVER executed.
**Data Shape:** analyzers hold a db handle for COMPILATION only; `RecordInsertSqlResult.mainInsert.compiled.sql` feeds EXPLAIN planning. The cast (`as unknown as`) documents that the analyzer's db is not the repository's runtime connection.

### Decisive source
```ts
// Build the INSERT statement using RecordInsertBuilder
const insertBuilder = new RecordInsertBuilder(analyzer.db as unknown as Kysely<DynamicDB>);
```
**Flow:** analyzer reconstructs domain Table + fieldValues from the command → builder compiles main INSERT + additional statements + lock metadata → analyzer explains/plans with the exact SQL production would run.
**Invariant:** The builder must be side-effect-free and deterministic — no clock reads, no id minting, no execution — because its output is treated as a pure function of (table schema, fieldValues, context). That purity is WHY one builder serves both the repository (execution) and explain tooling (analysis) with byte-identical SQL.
**Probe:** graph-verified consumers: `search_graph --name-pattern 'RecordInsertBuilder'` resolves both analyzer call sites; behavior pinned by CreateRecord/Paste e2e specs upstream (no unit spec in this environment — caveat recorded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "CreateRecordAnalyzer PasteCommandAnalyzer RecordInsertBuilder explain", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: keep write-SQL construction in a pure builder so EXPLAIN/dry-run surfaces reuse it verbatim. Adapt to your DI/db-handle conventions. Omit teable's command-explain pipeline specifics. Coverage caveat: consumer-level evidence via graph resolution; no direct runner here.
