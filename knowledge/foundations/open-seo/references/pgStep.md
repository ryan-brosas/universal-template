<!-- capsule-v2 -->
# pgStep — why doesn't AsyncLocalStorage reach Cloudflare Workflow steps, and what wraps step.do to fix it?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** How do you give every durable workflow step a DB client when each step resumes in its own execution context?

## Step-scoped Postgres wrapper
**Path/Symbol:** `src/server/workflows/pgStep.ts:pgStep` (:20-29).
**Signature:** `function pgStep<T extends Rpc.Serializable<T>>(step: WorkflowStep, name: string, config: WorkflowStepConfig | undefined, fn: () => Promise<T>): Promise<T>`.
**Data Shape:** Takes the engine's step handle, a unique step name, an optional config (`undefined` = engine default), and the step body; returns the persisted/replayed result bound by `Rpc.Serializable<T>` so outputs stay serializable.

### Decisive source
```ts
export function pgStep<T extends Rpc.Serializable<T>>(
  step: WorkflowStep,
  name: string,
  config: WorkflowStepConfig | undefined,
  fn: () => Promise<T>,
): Promise<T> {
  return config
    ? step.do(name, config, () => withPgClient(fn))
    : step.do(name, () => withPgClient(fn));
}
```

**Flow:** Every DB-touching step goes through `pgStep` → `withPgClient` opens a request-scoped Postgres client inside the step body → lazy postgres-js connect on first query → socket reclaimed when the invocation ends → in D1 mode `withPgClient` is a no-op so this degrades to plain `step.do`.
**Invariant:** The `AsyncLocalStorage` scope opened by `withPgClient` around the workflow's `run()` does NOT propagate into a step — steps are independently persisted and can resume in a fresh invocation. Each DB-touching step must open its own client; forgetting this yields "no PG scope" failures only on replay/resume, never on first run.
**Probe:** `src/server/workflows/RankCheckWorkflow.test.ts` (workflows run through pgStep-wrapped steps against stubbed repos; replay semantics pinned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "pgStep", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrapper shape and the ALS-does-not-cross-steps invariant for ANY durable-execution engine with per-step resumption (also applies to Temporal activities). Adapt `withPgClient` to your pool/client library and `Rpc.Serializable<T>` to your engine's serialization constraint. Omit the D1-mode no-op special case if you have no embedded-SQL fallback mode.
