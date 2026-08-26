<!-- capsule-v2 -->
# Layered fail-open config load + per-tier merge — how do global and project router configs combine without either clobbering the other?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** How must a two-layer (user-global ← per-project) JSON config be read, merged, and error-handled so a broken file never kills the extension?

## Fail-open parse → ordered merge → single normalize
**Path/Symbol:** `extensions/config.ts:parseConfigFile` (:49–71), `extensions/config.ts:loadRouterConfig` (:474–493), `extensions/config.ts:mergeConfig` (:99–128), `extensions/config.ts:mergeTier` (:89–97).
**Signature:** `parseConfigFile(path: string): ParsedConfigFile`; `loadRouterConfig(cwd: string): ConfigLoadResult`; `mergeConfig(base: RouterConfig, override: Partial<RouterConfig>): RouterConfig`; `mergeTier(existing?: RoutedTierConfig, next?: Partial<RoutedTierConfig>): RoutedTierConfig | undefined`.
**Data Shape:** Global file `join(getAgentDir(), 'model-router.json')`, project file `join(cwd, '.pi', 'model-router.json')`. `ParsedConfigFile = {config: Partial<RouterConfig>, warnings}`; `ConfigLoadResult = {config: RouterConfig, warnings: string[]}`.

### Decisive source
```ts
export const loadRouterConfig = (cwd: string): ConfigLoadResult => {
  const globalPath = join(getAgentDir(), 'model-router.json');
  const projectPath = join(cwd, '.pi', 'model-router.json');
  const globalResult = parseConfigFile(globalPath);
  const projectResult = parseConfigFile(projectPath);
  const baseConfig: RouterConfig = { profiles: {} };
  const merged = mergeConfig(
    mergeConfig(baseConfig, globalResult.config),
    projectResult.config,
  );
  const normalized = normalizeConfig(merged);
  return {
    config: normalized.config,
    warnings: [
      ...globalResult.warnings,
      ...projectResult.warnings,
      ...normalized.warnings,
    ],
  };
};
```
```ts
const mergeTier = (existing?, next?) => {
  if (!existing && !next) return undefined;
  if (!next) return existing;
  if (!existing) return next as RoutedTierConfig;
  return { ...existing, ...next };   // field-level tier override
};
```

**Flow:** missing file → `{config:{}, warnings:[]}` silently; unparseable JSON or non-object root → empty config + warning, never throw → merge global over `{profiles:{}}`, then project over that → normalize once → warnings concatenated in global→project→normalize order. Profile merge is per-name; within a profile, high/medium/low merge PER-TIER via spread so a project override replaces only the tiers it names. `models` merge shallow-by-alias (project alias wins whole). Scalars (`debug`, `phaseBias`, `rules`, …) are whole-value `??` — project `rules` REPLACE global rules, they do not concatenate.
**Invariant:** No input path may throw; every degradation is a warning string in one accumulated array, and the surviving config is always schema-shaped enough to normalize.
**Probe:** `extensions/config.test.ts` :94–120 (missing / invalid-json / not-object / valid), :140–177 (mergeConfig keeps base medium + adds override high), :302–313 (loadRouterConfig end-to-end with mocked fs: globalProfile.medium AND projectProfile.high both present).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "loadRouterConfig parseConfigFile merge global project", limit: 10 });
```

## Verdict
Adopt the fail-open parse contract, the global→project layering order, and per-tier spread merge verbatim; adapt file locations (`getAgentDir()`) and the `.pi/` project path to your host's config roots; omit nothing — the replace-not-concatenate semantics for scalar lists like `rules` are intentional and tested.
