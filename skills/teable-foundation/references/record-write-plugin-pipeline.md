<!-- capsule-v2 -->
# Record-write plugin pipeline — how does teable reuse prepared plugin state across a batched record write so repeated chunks don't re-derive it?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When a record write is processed in chunks, how does the plugin runner let an operation-only plugin fast-path chunk prepare by reusing the previous prepared state instead of recomputing it?

## Prepared-state reuse across chunked writes
**Path/Symbol:** `packages/v2/core/src/application/services/RecordWritePluginRunner.ts` — `RecordWritePluginRunner.prepare` (461–500), `.preparePlugin` (502–578), `.resolvePlugins` (580–612); `RecordWritePluginExecution.guard` (255–303), `.beforePersist` (304–310), `.afterCommit` (311–360), `.getPreparedStateFor` (used at 481).
**Signature:** `prepare(context: RecordWritePluginContext, options?: {previousExecution?: RecordWritePluginExecution; runnerOptions?: RecordWritePluginRunnerOptions}): Promise<Result<RecordWritePluginExecution, DomainError>>`.
**Data Shape:** same enforce-grouped shape as field-operation, PLUS: plugins may implement `scope?(ctx, preparedState)→Result<scope>`; `prepare` accepts an optional `previousExecution` whose per-plugin prepared state is fed back into the next `prepare` call as `previousPreparedState`; `runnerOptions` can skip plugins by name.

### Decisive source
```ts
// prepare: feed the previous execution's per-plugin prepared state into the next prepare
for (const group of createEnforceGroups(matchedPlugins, (plugin) => plugin.enforce)) {
  const results = await Promise.all(group.map((plugin) =>
    this.preparePlugin(plugin, context, options?.previousExecution?.getPreparedStateFor(plugin))));
  ...
}
// preparePlugin: prepare then scope, both with the (possibly reused) preparedState
if (plugin.prepare) { /* ... preparedState = result.value */ }
if (plugin.scope) { /* ... scope = result.value */ }
return ok({ plugin, preparedState, scope });
```
**Flow:** identical enforce-grouped orchestration to `field-operation-plugin-pipeline.md`, with two additions: (1) `prepare` accepts a `previousExecution` and feeds each plugin's prior prepared state into the next prepare call — so an operation-only plugin (one whose prepare result doesn't change across chunks) can fast-path by reusing state instead of recomputing; (2) plugins may declare a `scope` hook that runs after prepare with the same prepared state. `runnerOptions` lets a caller skip specific plugins for a given write.
**Invariant:** prepared state is private to the owning plugin but reusable across chunked writes via `previousExecution`; an operation-only plugin can skip re-preparing when its state is stable; `scope` runs after prepare with the same prepared state; afterCommit remains fail-open; contexts stay detached.
**Probe:** `packages/v2/core/src/application/services/RecordWritePluginRunner.spec.ts` — `"passes the previous prepared state back into a later prepare call"` (:325), `"lets an operation-only plugin fast-path chunk prepare by reusing the previous state"` (:380), `"skips plugins listed in runner options"` (:258), `"logs afterCommit failures without failing the command path"` (:596), `"passes a detached table snapshot to each plugin hook"` (:901).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "RecordWritePluginRunner prepare previousExecution getPreparedStateFor", limit: 10,, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the enforce-grouped pipeline plus the `previousExecution` prepared-state-reuse contract and the optional `scope` hook. Adapt the plugin interface and enforce levels. Omit teable's specific record-write plugins and tracing. This is the record-write sibling of `field-operation-plugin-pipeline.md`; Table/View runners share the same core.
