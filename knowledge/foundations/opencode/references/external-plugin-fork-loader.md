<!-- capsule-v2 -->
# External plugin fork loader — how do you load third-party plugin modules without letting one bad package break boot?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A host must load user-configured plugin packages (npm specs, file paths, directory glob files), validate their module shape, and register them — but a broken package, missing entrypoint, or invalid export must never prevent boot. How is that isolation structured?

## Background fork + per-plugin ignoreCause + promise bridge
**Path/Symbol:** `packages/core/src/config/plugin/external.ts` (source collection :30-60, resolution+import loop :62-88, `Effect.forkScoped` :89, `PluginModule` schema :17-31), `packages/core/src/plugin/promise.ts` (`fromPromise` :22-93, scope-attached registration :30-33), `packages/core/src/plugin/host.ts` (`plugin.add` :196-198).
**Signature:** `PluginModule = { default: { id: string, effect: fn } | { id: string, setup: fn } }`; `fromPromise(plugin: Plugin) → EffectPlugin`; `npm.add(spec) → { directory, entrypoint }`.
**Data Shape:** config `plugins` entries are `string | {package, options?}`; `file://`/`./`/`../` resolve relative to the document's directory; directory entries glob `{plugin,plugins}/*.{ts,js}` sorted.

### Decisive source
```ts
// config/plugin/external.ts:74-89 — per-plugin isolation + background fork
for (const ref of configured) {
  yield* Effect.gen(function* () {
    const entrypoint = path.isAbsolute(ref.package)
      ? pathToFileURL(ref.package).href
      : (yield* npm.add(ref.package)).entrypoint
    if (!entrypoint) return
    const mod = yield* Effect.promise(() => import(entrypoint))
    const value = (yield* Schema.decodeUnknownEffect(PluginModule)(mod)).default
    const plugin = "effect" in value ? value : PluginPromise.fromPromise(value)
    yield* ctx.plugin.add({
      id: plugin.id,
      effect: (host) => plugin.effect({ ...host, options: ref.options ?? {} }),
    })
  }).pipe(Effect.ignoreCause)   // one bad plugin never blocks the rest
}).pipe(Effect.forkScoped({ startImmediately: true }))  // boot never waits for npm
```

**Flow:** The plugin collects all configured references first (document `plugins` arrays with file:// / relative / bare-package resolution, plus sorted directory glob files), then forks the WHOLE load loop into a background scoped fiber with `startImmediately: true` — boot continues while npm installs and dynamic imports happen. Inside the loop each reference is its own `Effect.gen` wrapped in `Effect.ignoreCause`: a missing entrypoint, a failed npm install, a throwing dynamic import, or a schema-invalid module default is swallowed (cause logged by ignoreCause semantics) and the NEXT plugin still loads. Absolute paths become `file://` URLs; bare specs go through `npm.add` which resolves/installs and returns the entrypoint. Module validation is structural: `default.effect` (Effect plugin, used as-is) or `default.setup` (Promise plugin, adapted via `PluginPromise.fromPromise`). Options injection happens by wrapping: `plugin.effect({...host, options: ref.options ?? {}})` — the host object is shared, options are per-registration. The promise bridge captures the fiber context and scope at adaptation time; every hook registration runs `Scope.provide(scope)(effect)` so hook disposals attach to the plugin's scope (unloading the plugin disposes its hooks), and promise-returning callbacks are lifted with `Effect.promise`. The comment pins the batching design: captured context preserves boot-time batching so Promise-plugin transforms still coalesce into one reload per domain.
**Invariant:** boot never waits on external plugin loading (background fork); a broken plugin never blocks later plugins (per-plugin ignoreCause); hook registrations are scope-attached (unload disposes); options are per-registration, never global.
**Probe:** `packages/core/test/config/plugin.test.ts` (248L, 5 `it.live`): "ignores invalid plugins and continues loading" pins missing + invalid fixtures followed by a good fixture still loading (via the `waitForAgent` poll loop that tolerates the background fork); "installs and resolves npm plugin packages" pins the npm.add path with a stubbed Npm service; "loads plugin files from config directories" pins the directory glob source. Source pin:
```bash
grep -c 'forkScoped'  packages/core/src/config/plugin/external.ts  # expect 1
grep -c 'ignoreCause' packages/core/src/config/plugin/external.ts  # expect 1
grep -c 'npm.add'     packages/core/src/config/plugin/external.ts  # expect 1
grep -c 'it.live'     packages/core/test/config/plugin.test.ts     # expect 5
grep -c 'waitForAgent' packages/core/test/config/plugin.test.ts    # expect 6
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "ConfigExternalPlugin forkScoped ignoreCause npm.add PluginPromise.fromPromise dynamic import entrypoint PluginModule schema validation scope-attached hook registration", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the background fork + per-plugin ignoreCause isolation, the structural two-shape module validation, options-by-wrapping, and the scope-attached promise bridge. Adapt `npm.add` to the host's package manager and the glob patterns to its plugin directory convention. Omit the file:// special case if the host never loads local paths. Coverage caveat: the promise-bridge batching claim is source-comment-confirmed (promise.ts :18-21) with no dedicated test pinning coalescing; Codebase Memory MCP not connected this session, Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
