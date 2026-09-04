<!-- capsule-v2 -->
# Field-operation plugin pipeline — how does teable run a set of field-operation plugins through ordered, enforce-grouped phases without leaking state between them?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a plugin runner filter, prepare, guard, and commit hooks for a field mutation so that plugins run in a deterministic order, share no mutable state, and never break the command path on afterCommit failure?

## Enforce-grouped phase orchestration
**Path/Symbol:** `packages/v2/core/src/application/services/FieldOperationPluginRunner.ts` — `FieldOperationPluginRunner.prepare` (575–602), `.preparePlugin` (604–640), `.resolvePlugins` (642–668); `FieldOperationPluginExecution.guard` (418–420), `.beforePersist` (422–430), `.afterCommit` (432–475), `.runPhase` (477–508), `.invokePhaseHook` (510–549); helpers `enforceOrder` (36), `createEnforceGroups` (53–62).
**Signature:** `prepare(context: FieldOperationPluginContext): Promise<Result<FieldOperationPluginExecution, DomainError>>`; phases `'supports'|'prepare'|'guard'|'beforePersist'|'afterCommit'`.
**Data Shape:** each plugin implements `{name, enforce?: 'first'|'normal'|'last', supports(kind), prepare?(ctx)→Result<state>, guard?(ctx,state)→Result, beforePersist?(ctx,state)→Result, afterCommit?(ctx,state)→Result}`. `createEnforceGroups` buckets plugins by `enforceOrder` so same-enforce plugins run in parallel within a group and groups run serially in enforce order.

### Decisive source
```ts
// prepare: within each enforce group, prepare in parallel; fail fast on first group error
for (const group of createEnforceGroups(matchedPlugins, (plugin) => plugin.enforce)) {
  const results = await Promise.all(group.map((plugin) => this.preparePlugin(plugin, context)));
  for (const result of results) if (result.isErr()) return err(result.error);
  preparedPlugins.push(...results.map(r => r.value));
}
// guard/beforePersist: beforePersist short-circuits serially; guard runs per enforce group in parallel
// afterCommit: fail-open — log, never throw; Promise.allSettled per enforce group
for (const group of createEnforceGroups(this.preparedPlugins, (e) => e.plugin.enforce)) {
  const tasks = group.filter(e => e.plugin.afterCommit).map(async (entry) => {
    try { const r = await entry.plugin.afterCommit!.call(entry.plugin, ctx, entry.preparedState);
          if (r.isErr()) this.logAfterCommitError(...); }
    catch (e) { this.logAfterCommitError(...); } });
  await Promise.allSettled(tasks);
}
```
**Flow:** `prepare` → `resolvePlugins` (filter by `supports(context.kind)`, sort by enforce order) → per enforce group, prepare in parallel, fail-fast on first error → build `FieldOperationPluginExecution` with a **sanitizer** that detaches table targets (passes a detached snapshot, never the live table). Then `guard` (per enforce group, parallel, first error aborts and skips later groups), `beforePersist` (serial in enforce order, short-circuits on first error), `afterCommit` (per enforce group, parallel, **fail-open**: errors are logged, never propagated). Every hook receives `(pluginContext, preparedState)` where `preparedState` is private to its owning plugin.
**Invariant:** same-enforce plugins run in parallel and enforce groups run serially in `first→normal→last` order; `beforePersist` short-circuits on the first plugin error while `guard` aborts remaining enforce groups; `afterCommit` can NEVER fail the command path (errors logged only); plugin contexts are sanitized to detached table snapshots so plugins cannot mutate live tables; prepared state is never shared between plugins.
**Probe:** `packages/v2/core/src/application/services/FieldOperationPluginRunner.spec.ts` — `"orders plugins by enforce then registration order"` (:179), `"returns the first guard error in group order and skips later enforce groups"` (:273), `"short-circuits beforePersist on the first plugin error"` (:334), `"logs afterCommit failures without changing success"` (:453), `"passes detached table targets to plugins without mutating live tables"` (:743).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "FieldOperationPluginRunner FieldOperationPluginExecution createEnforceGroups", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the enforce-grouped phase pipeline: supports-filter → parallel-in-group/serial-across-group prepare, fail-fast guard, short-circuit beforePersist, fail-open afterCommit, and detached-context sanitization. Adapt the phase vocabulary and enforce levels. Omit teable's specific field-operation plugins and tracing spans. This is one of four sibling runners (Field/Record/Table/ViewOperationPluginRunner) sharing the same `createEnforceGroups` core — see `record-write-plugin-pipeline.md` for the prepared-state-reuse variant.
