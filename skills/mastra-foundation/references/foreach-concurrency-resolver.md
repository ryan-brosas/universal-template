<!-- capsule-v2 -->
# Foreach concurrency resolver — static number or input-derived function with floor-at-1 fallback

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** How is the effective foreach concurrency computed and what must invalid configurations degrade to?

## Invalid or non-positive resolves to sequential, never throws
**Path/Symbol:** `packages/core/src/workflows/utils.ts:resolveForeachConcurrency` (:786-796).
**Signature:** `resolveForeachConcurrency(opts: ForeachOptions | undefined, context: ForeachConcurrencyContext): number` where context = `{ inputData: any; getInitData: () => any }`.
**Data Shape:** configured value may be a plain number OR a `ForeachConcurrencyResolver` function evaluated at EXECUTION time with run input access (declared at `.foreach(step, { concurrency })`).

### Decisive source
```ts
export function resolveForeachConcurrency(
  opts: ForeachOptions | undefined,
  context: ForeachConcurrencyContext,
): number {
  const configured = opts?.concurrency ?? 1;
  const resolved = typeof configured === 'function' ? configured(context) : configured;
  if (typeof resolved !== 'number' || !Number.isFinite(resolved) || resolved < 1) {
    return 1;
  }
  return Math.floor(resolved);
}
```

**Flow:** default 1 when opts absent → invoke resolver with `{inputData, getInitData}` if functional → validate → `Math.floor`. The executor calls it BEFORE span creation so the loop span attribute records the RESOLVED concurrency (:932-935 + :956).
**Invariant:** NaN/Infinity/0/negative/strings ALL collapse to 1 (sequential) rather than throwing — an invalid concurrency config degrades throughput, never correctness. Fractional values floor. Because resolvers run per execution, the same workflow can adapt concurrency to payload size (e.g. `ctx => ctx.inputData.length > 100 ? 10 : 1`).
**Probe:** `sed -n '790,796p' packages/core/src/workflows/utils.ts | grep -c 'return 1'` from repo root (=1). Direct test anchor: `packages/core/src/workflows/foreach-failure-progress.test.ts:65 '.foreach(processItem, { concurrency })'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "resolveForeachConcurrency ForeachConcurrency", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the resolver contract + floor-at-1 validation verbatim (11 lines, fully portable). Adapt the context fields you can expose. Omit nothing.
