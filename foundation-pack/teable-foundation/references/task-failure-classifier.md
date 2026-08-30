<!-- capsule-v2 -->
# Task failure classifier — which background-task errors are retryable and which must dead-letter on first occurrence?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Given a DomainError escaping a task execution, how do you decide retry vs immediate dead-letter without a human?

## classifyComputedTaskFailure
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedTaskFailureClassifier.ts:47–81` — `classifyComputedTaskFailure(error): {failureKind, failureReason, retryable}`; pattern table `SQL_GENERATION_BUG_PATTERNS` (:27–35); timeout matcher (:37–45); diagnostics builder in worker `buildFailureDiagnostics` (ComputedUpdateWorker.ts:89–101).
**Signature:** kinds = `'transient'|'statement_timeout'|'computed_code_bug'|'data_safety_limit'`; reasons = `'unknown'|'statement_timeout'|'postgres_sql_generation_error'|'computed_cell_value_max_bytes'`.
**Data Shape:** Input is the DomainError (message + optional code). Output classification drives `markFailed(..., {directDeadLetter, diagnostics})`; diagnostics envelope `{version: 1, failure: {kind, reason, retryable, directDeadLetter, phase}, execution?: PostgresSqlExecutionDiagnostics}`.

### Decisive source
```ts
if (error.code === 'validation.limit.computed_cell_value_max_bytes') {
  return { failureKind: 'data_safety_limit', failureReason: 'computed_cell_value_max_bytes', retryable: false };
}
if (isStatementTimeoutMessage(message)) {
  return { failureKind: 'statement_timeout', failureReason: 'statement_timeout', retryable: false };
}
```
```ts
const SQL_GENERATION_BUG_PATTERNS: ReadonlyArray<RegExp> = [
  /cannot cast type .+ to .+/,
  /operator does not exist:/,
  /function .+ does not exist/,
  /syntax error at or near/,
  /case types .+ cannot be matched/,
  /column .+ does not exist/,
  /missing from-clause entry for table/,
];
```

**Flow:** data-safety-limit by error CODE → statement timeout by normalized-message match (pg code `57014`, 'statement timeout', 'canceling statement due to statement timeout') → deterministic SQL-generation bugs by regex table over the lowercased message → everything else `transient`/retryable. The worker converts non-retryable into immediate dead-letter WITH phase-tagged diagnostics; retries only happen for transient.
**Invariant:** Statement timeouts are NON-retryable here — a timeout will reproduce deterministically against the same data volume; retrying would burn the attempt ladder without changing the outcome. The regex list is intentionally message-based because pg error classes arrive as text after driver wrapping. Unknown errors default to RETRYABLE (fail toward resilience, not the dead letter).
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedTaskFailureClassifier.spec.ts` (:7 sql-gen bugs non-retryable code bugs, :22 timeouts separately non-retryable, :36 cell-limit non-retryable, :51 unknown infrastructure errors stay retryable).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "classifyComputedTaskFailure ComputedTaskFailureClassification", limit: 10 });
```

## Verdict
Adopt the four-kind taxonomy, code-first/message-second matching, timeouts-as-deterministic posture, unknown-implies-retryable default, and the versioned diagnostics envelope; adapt the regex table to your database's error vocabulary; omit nothing — the module is self-contained.
