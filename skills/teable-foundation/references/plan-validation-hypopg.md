<!-- capsule-v2 -->
# Hypothetical-index plan validation — how does teable prove a recommended index helps before creating it, and what safety gates guard the EXPLAIN input?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** You want to validate an index candidate against the planner without creating it. How do you build the hypothetical CREATE INDEX, run EXPLAIN before/after, and refuse unsafe SQL?

## HypoPG before/after EXPLAIN with a strict SQL allowlist
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/planValidation.ts` — `PostgresTableQueryPlanValidator.validate` (35–146), `validateExplainSql` (158–164), `explain` (166–174), `parseExplainPlan` (176–190), `buildHypotheticalIndexStatement` (239–263), `readHypopgSchema` (222–233), `resetHypopg` (235–237); `searchVector.ts` `validatePlan` (726–844) is the substring-search twin.
**Signature:** `validate(ctx, {table, observation, indexInspection}): Promise<Result<TableQueryPlanValidation, DomainError>>`.
**Data Shape:** outcome = `{status:'validated'|'skipped'|'failed', method:'explain'|'hypothetical_index', reason, candidateCount, startupCostBefore/After, totalCostBefore/After, planNodeBefore/After, usesCandidateIndex, indexStatements[], errors[]}`.

### Decisive source
```ts
const validateExplainSql = (statement) => {
  const trimmed = statement.trim();
  if (trimmed.includes(';')) return 'multi_statement_sql_unsupported';
  if (!/^(?:select|with)\b/i.test(trimmed)) return 'non_select_sql_unsupported';
  if (/\$\d+\b/.test(trimmed)) return 'parameterized_sql_unsupported';
  return undefined;
};
// hypothetical index only for btree / gin_trgm candidates with a resolvable field:
const fields = candidate.fields?.filter(f => f.fieldDbName) ?? (candidate.fieldDbName ? [{fieldDbName: candidate.fieldDbName}] : []);
if (fields.length === 0) return undefined;
if (candidate.kind === 'gin_trgm') return `CREATE INDEX ON ${tableSql} USING gin (${quote(fields[0].fieldDbName)} gin_trgm_ops)`;
if (candidate.kind === 'btree') return `CREATE INDEX ON ${tableSql} USING btree (${fields.map(f => `${quote(f.fieldDbName)}${f.direction ? ' '+f.direction.toUpperCase() : ''}`).join(', ')})`;
// hypopg_create_index is schema-qualified from the discovered hypopg schema:
await sql`SELECT * FROM ${sql.raw(quoteIdentifier(hypopgSchema))}.hypopg_create_index(${statement})`.execute(db);
```

**Flow:** read the normalized SQL sample from the observation's `sqlDiagnostics` (skip if absent) → `validateExplainSql` gates (no `;`, SELECT/WITH only, no `$n` params) → build one hypothetical index per missing-index candidate → if none, return `validated/explain/no_hypothetical_index_candidates` → discover the hypopg schema via `pg_proc` (`proname='hypopg_create_index'`), skip to explain-only if absent → `hypopg_reset()` → create each hypothetical index → EXPLAIN (FORMAT JSON) before and after → `hypopg_reset()` → compute `usesCandidateIndex` from `Index Name` or `<...>` hypothetical markers → return validated with cost deltas.
**Invariant:** EXPLAIN input is strictly gated (single SELECT/WITH, no parameters, no semicolons) so the advisor can never run a mutating statement; the hypothetical index is always reset in a `finally`; HypoPG's inability to model GIN degrades to explain-only (keeps `needs_plan_validation`) rather than failing the whole analysis.
**Probe:** `planValidation.spec.ts:13` `describe('PostgresTableQueryPlanValidator')` — `:14` 'skips validation without a normalized SQL sample'; `searchVector.spec.ts` `chooseScopedExpressionNextAction`/`assertReadySearchVectorExecutionRecommendation` pin the validated-vs-not decision.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableQueryPlanValidator validateExplainSql buildHypotheticalIndexStatement hypopg", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the EXPLAIN allowlist + HypoPG before/after cost-delta validation with always-reset hypothetical indexes and graceful GIN-unsupported degradation; adapt the SQL grammar gate to host dialect; omit teable's observation-window plumbing if the host samples SQL elsewhere. Coverage: `planValidation.ts` is parse_partial at :225 (one template-literal line); cited ranges otherwise indexed.
