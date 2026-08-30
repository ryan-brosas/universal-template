<!-- capsule-v2 -->
# Plugin store & ordering — how are plugins validated, ordered (before/enforce/pre/post) and removed without breaking environment scoping?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know the exact ordering pipeline (registration order → enforce groups → dependency topo sort) and why `remove` is resolved as a separate pass before any `setup` runs.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/pluginManager.ts:validatePlugin` (12–55), `isEnvironmentMatch` (61–64), `createPluginManager` (66–132), `sortPluginsByEnforce` (137–155), `sortPluginsByDependencies` (162–226), `initPlugins` (228–294).
**Signature:** `createPluginManager(logger): PluginManager`; `initPlugins({context, pluginManager}): Promise<void>`.
**Data Shape:** internal store is `PluginMeta[] = {instance: RsbuildPlugin, environment?: string}[]`; plugin contract `{name, setup, apply?, enforce?, pre?, post?, remove?}`.

### Decisive source
```ts
// validatePlugin: friendliest error path — webpack-style plugins get pointed at tools.rspack
if (isFunction((plugin as Rspack.RspackPluginInstance).apply)) {
  const { name = 'SomeWebpackPlugin' } = (plugin as Rspack.RspackPluginInstance).constructor || {};
  throw new Error(`${name} looks like a webpack or Rspack plugin, please use \`tools.rspack\` to register it: ...`);
}
```
```ts
// initPlugins ordering + remove resolution
let plugins = pluginManager.getAllPluginsWithMeta();
plugins = sortPluginsByEnforce(plugins);
plugins = sortPluginsByDependencies(plugins);

const removedPlugins = new Set<string>();
const removedEnvPlugins: Record<string, Set<string>> = {};
for (const { environment, instance } of plugins) {   // pass 1: collect removals
  if (!instance.remove) continue;
  ...
}
for (const { instance, environment } of plugins) {   // pass 2: run setups
  if (removedPlugins.has(name) || (environment && removedEnvPlugins[environment]?.has(name))) continue;
  // action gate: apply:'serve' maps dev+preview→serve; function form gets (originalConfig,{action})
  await setup(context.getPluginAPI!(environment));
}
```
```ts
// cycle detection in sortPluginsByDependencies
if (allLines.length) {
  throw new Error(`... Plugins dependencies has loop: ${Object.keys(restInRingPoints).join(',')}`);
}
```

**Flow:** addPlugins validates each non-null entry, inserts with optional `{before}` name splice (missing anchor logs a warn and appends instead of throwing), else appends. At init time order is computed in three stages: registration order preserved inside each bucket by stable partitioning into pre/normal/post (`enforce`), then Kahn-style topo sort where edges come from every plugin's `pre:[names]` (edges name→plugin) and `post:[names]` (edges plugin→name); zero-in-degree queue seeded from all unconnected plugins keeps deterministic order; leftover edges = loop, thrown with participant names. Removals declared via `remove` are collected globally or per-environment BEFORE setup runs — an env-scoped plugin may only remove other same-env plugins while a global plugin removes anything. The `apply` field gates per-action execution: `'build'` matches only build; `'serve'` matches dev AND preview (via `applyMap`); function form receives `(originalConfig, {action})` and returns truthiness.

**Invariant:** `remove`/ordering never depends on setup side effects — the whole plan is computed from declarations before any hook taps exist; environment matching is exact-equality-or-undefined (`undefined` matches all environments).

**Probe:** `tests/pluginStore.test.ts:5-47` pins final setup order `[2,0,3,1]` for mixed pre/post declarations; `:49-84` pins remove-before-setup; `:86-138` pins that an environment plugin cannot remove a global one but a global can remove env ones; `tests/pluginDependencies.test.ts:119-137` pins the loop error `/Plugins dependencies has loop: 2,3,5/`; `:139-179` pins duplicate names across environments staying distinct entries; `tests/pluginApply.test.ts:32-63` pins the serve/dev/preview mapping.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "sortPluginsByDependencies createPluginManager initPlugins validatePlugin", limit: 10 });
```

## Verdict
Adopt the meta-store shape, three-stage ordering, declarative remove pass, and action gating as portable contracts for any tool plugin system. Adapt the specific error copy and `tools.rspack` hint. Omit rsbuild's concrete default-plugin list (product). Coverage caveat: no test-runner execution this run; probes cited from on-disk specs.
