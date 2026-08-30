<!-- capsule-v2 -->
# safeTry Result funnel — how do handlers chain six fallible steps without try/catch noise or lost errors?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the teable-v2 idiom for composing neverthrow Results across async repository/policy calls inside one handler?

## Generator-based yield* rail with bound this
**Path/Symbol:** `packages/v2/table-query-ops/src/application.ts` (all seven handlers, e.g. `AnalyzeAndRecommendTableQueryHandler.handle` :204-245); helpers `safeTry`, `err`, `ok` from neverthrow; type-only port imports (:30-43 with the tsdown comment).
**Signature:** `async function* (this: Handler) { const a = yield* await step(); …; return ok(result); }` wrapped as `return safeTry<T, DomainError>(fn.bind(this))`.
**Data Shape:** every step returns `Promise<Result<T, DomainError>>`; `yield*` short-circuits on the FIRST Err and makes it the handler's return; domain validation (`TableId.create`) participates in the same rail.

### Decisive source
```ts
return safeTry<AnalyzeAndRecommendTableQueryResult, DomainError>(
  async function* (this: AnalyzeAndRecommendTableQueryHandler) {
    const tableId = yield* parseTableId(command.observation.tableId());
    const table   = yield* await this.tableRepository.findOne(context, TableByIdSpec.create(tableId));
    const physicalStats    = yield* await this.physicalStatsReader.read(context, table);
    const indexInspection  = yield* await this.indexInspector.inspect(context, table, command.observation.shape());
    const planValidation   = yield* await this.planValidator.validate(context, { table, observation: command.observation, indexInspection });
    const report           = yield* this.riskPolicy.evaluate({ observation: command.observation, physicalStats, indexInspection, planValidation });
    if (!report.shouldRecommend()) return ok({ report });   // early success exit INSIDE the rail
    const recommendation = yield* TableQueryRecommendation.createOpen({ observation: command.observation, report, now: this.clock.now() });
    const saved = yield* await this.recommendationRepository.save(context, recommendation);
    return ok({ report, recommendation: saved });
  }.bind(this)
);
```

**Flow:** sync domain parses and async repo reads share ONE rail → first error wins and propagates as the handler's Err → success paths return `ok(...)` from the generator body.
**Invariant:** Handlers NEVER throw for expected domain failures; ports are imported type-only so interface-only modules don't emit runtime imports under tsdown/esbuild bundlers (copy that eslint-disable + comment when porting). The executor-failure-is-state pattern (RunTableQueryRemediationTaskHandler :348-372) is the sanctioned exception: it deliberately inspects `executed.isErr()` to CONVERT the failure into a task state instead of letting the rail short-circuit.
**Probe:** no dedicated spec file for application.ts — behavior pinned indirectly via domain.spec advisor matrix + di.spec wiring tests. Coverage caveat recorded.
**Coverage caveat:** application-layer handlers have no direct unit spec at this HEAD; their contract is pinned through the domain specs and DI registration spec.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "AnalyzeAndRecommendTableQueryHandler handle safeTry", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the safeTry generator rail wholesale — it is the house style of the entire v2 rewrite and the reason its error handling stays uniform; adapt naming; omit nothing.
