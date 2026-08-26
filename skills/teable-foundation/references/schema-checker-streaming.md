<!-- capsule-v2 -->
# Streaming integrity checker — how do you validate hundreds of rules against a live DB without blocking the event loop or lying about dependency failures?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the checker turn rule results into a UI-ready stream while keeping optional-rule failures from cascading?

## SchemaChecker async generator
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/checker/SchemaChecker.ts` — `checkTable` (:50–159), `checkField` (:165–279), `getRuleValidationCtx` (:27–33); result factory `rules/checker/SchemaCheckResult.ts`.
**Signature:** `async *checkTable(table): AsyncGenerator<SchemaCheckResult>`; result = `{id: fieldId:ruleId, status: 'pending'|'running'|'success'|'error'|'warn', required, dependencies, depth, message?, details?, repair?, timestamp}`.
**Data Shape:** depth comes from planner `ruleDepths` (UI tree nesting); every yield carries the full pending envelope so consumers can render progress before completion.

### Decisive source
```ts
const yieldToEventLoop = () => new Promise<void>((r) => setImmediate(r)); // :20

// ASYMMETRIC dependency gate — the load-bearing subtlety:
const dependenciesSatisfied = rule.dependencies.every(
  (depId) => validatedRules.get(depId) === true);
if (!dependenciesSatisfied) {
  if (rule.required) { yield errorResult(pending, 'Skipped: dependencies not satisfied');
    validatedRules.set(rule.id, false); }        // ← failure propagates
  else { yield warnResult(pending, 'Skipped: dependencies not satisfied');
    validatedRules.set(rule.id, true); }         // ← optional failure does NOT block children
  continue;
}
```

**Flow:** plan table → per entry: yield pending → check deps gate → yield running → `rule.isValid` with ctx swapped to `metaDb` when `rule.validationScope === 'meta'` → valid⇒success / invalid⇒error+repair-hint (required) or warn+repair-hint (optional) → thrown exceptions caught and converted to error results (never kill the stream) → `setImmediate` between EVERY rule keeps Node responsive during long DB probes.
**Invariant:** an optional rule that fails is recorded as `true` in `validatedRules` — dependents of an optional rule must still be CHECKED, only dependents of a FAILED REQUIRED rule are skipped; repair hints at check time are computed with `{skipStatementCheck: true}` so hint computation never executes `up()`.
**Probe:** no dedicated checker unit spec — behavior pinned indirectly via repairer pglite specs + `SchemaRuleResolver.spec.ts`; deterministic probe = `get_code_snippet SchemaChecker.checkTable` (:50-159).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "SchemaChecker checkTable pendingResult warnResult validationScope meta", limit: 10 });
```

## Verdict
Adopt the streaming pending→running→terminal protocol, the asymmetric optional-dependency gate, per-rule meta-plane swap, exception-to-error-result containment, and event-loop yields; adapt statuses/colors to your UI vocabulary; omit the i18n message envelope if host has single-locale output.
