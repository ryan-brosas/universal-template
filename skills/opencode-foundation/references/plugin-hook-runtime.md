<!-- capsule-v2 -->
# Plugin hook runtime — how do loaded plugins become ordered hooks with error isolation and cleanup?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How does the host turn plugin modules into a deterministic hook chain, isolate their failures, and dispose them?

## Hook aggregation & trigger
**Path/Symbol:** `packages/opencode/src/plugin/index.ts` (`applyPlugin`, state machine, `trigger`, finalizers; lines 112-308).
**Signature:** `trigger<Name>(name, input, output): Effect<Output>` — mutates `output` in place through each registered hook of that name.
**Data Shape:** State = `{ hooks: Hooks[] }` per instance (InstanceState.make). Hooks come from three sources in fixed order: built-in internal plugins (11 auth/gateway plugins, skippable via `disableDefaultPlugins`), then external npm/file plugins, then a `config` notification pass over ALL hooks.

### Decisive source
```ts
// index.ts:217-240 — sequential application after parallel loading
for (const load of loaded) {
  if (!load) continue
  // Keep plugin execution sequential so hook registration and execution
  // order remains deterministic across plugin runs.
  yield* Effect.tryPromise({
    try: () => applyPlugin(load, input, hooks),
    catch: (err) => { const message = errorMessage(err); return message },
  }).pipe(
    Effect.tapError((error) => Effect.logError("failed to load plugin", { path: load.spec, error })),
    Effect.catch(() => Effect.void),
  )
}
```

**Flow:** loadExternal runs candidates in parallel → applyPlugin walks results SEQUENTIALLY (v1 default export `{id?, server?}` wins over legacy named exports; legacy module exports deduped by identity via Set so `export default run; export const named = run` registers once) → every failure is caught, logged, optionally published as a session error event (`publishPluginError` with stage-specific messages: install failures render as `pkg@version`) → after all hooks register, each gets `hook.config(cfg)` → an event subscription fans bus events to `hook["event"]` filtered by directory → two finalizers: unsubscribe + `hook.dispose?.()` per hook, both error-isolated.
**Invariant:** Hook REGISTRATION is sequential for determinism even though loading was parallel; a throwing plugin init must never abort siblings (`Effect.option` swallows internal-plugin errors; external errors log+continue — pinned by `"continues loading plugins when plugin init throws"` / `"...module has invalid export"` / `"...import fails"`). `flags.pure` drops all external plugins entirely. Trigger hooks follow the `(input, output) => Promise<void>` shape derived by the `TriggerName` mapped type — anything else isn't triggerable.
**Probe:** `packages/opencode/test/plugin/loader-shared.test.ts` :666/:710/:746 (failure isolation trio), :852 (`"initializes server plugins in config order"`), :903 (`"skips external plugins in pure mode"`), :103 (`"deduplicates same function exported as default and named"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Plugin Service trigger hooks applyPlugin", limit: 8 });
```

## Verdict
Adopt parallel-load/sequential-register ordering, per-hook error isolation at every phase (init/config/event/dispose), and v1-default-export precedence. Adapt hook naming and the output-mutation trigger convention to your host API. Omit the Effect/Layer wiring (InstanceState, LayerNode) — substitute your own DI/lifecycle scope but keep the finalizer pairing of subscribe→unsubscribe.
