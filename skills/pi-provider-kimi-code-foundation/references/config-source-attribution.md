<!-- capsule-v2 -->
# Config source attribution — how do you tell users WHICH layer produced each effective config value?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** After merging defaults/home/project/env/runtime layers, how do you answer "where did this value come from?" for every leaf field without re-running the merge?

## Config source attribution
**Path/Symbol:** `src/config.ts:440-487` (`hasPath`, `sourceForPath`, `buildSources`); interface `KimiCodeConfigSources` :67-84; entry `loadKimiCodeConfigSources` :525-529; source tag type `KimiConfigSource` :10.
**Signature:** `hasPath(config: Record<string, unknown>, path: readonly string[]): boolean`; `sourceForPath(layers, path): KimiConfigSource`; `buildSources(layers): KimiCodeConfigSources`.
**Data Shape:** a mirror of the config tree where every leaf is replaced by its origin tag: `"runtime" | "env" | "project" | "home" | "default"` — e.g. `sources.tools.moonshot_search.enabled` is one tag.

### Decisive source
```ts
function hasPath(config: Record<string, unknown>, path: readonly string[]): boolean {
  let current: unknown = config;
  for (const key of path) {
    if (!isRecord(current) || !Object.hasOwn(current, key)) return false;
    current = current[key];
  }
  return true;
}

function sourceForPath(
  layers: Array<{ source: KimiConfigSource; config: Record<string, unknown> }>,
  path: readonly string[],
): KimiConfigSource {
  for (let i = layers.length - 1; i >= 0; i--) {
    if (hasPath(layers[i].config, path)) return layers[i].source;
  }
  return "default";
}
```

**Flow:** instead of replaying the merge, walk each leaf's JSON-pointer-style path
(`["model","generation","temperature"]`, `["tools", name, "enabled"]`, …) through the
layer array from HIGHEST precedence to lowest; the first layer whose raw config owns that
exact path wins the attribution. Paths absent from every layer report the `"default"`
sentinel. Because it probes the same raw layer objects that `loadLayers` produced, the
attribution is consistent with merge semantics by construction: the highest layer that
*has* the path is also the one whose value survives the deep merge (leaf-replace).
**Invariant:** ownership is decided per LEAF PATH with `Object.hasOwn` (inherited or
prototype properties never count); a partial object in a high layer (e.g. project sets
`tools.moonshot_search.default_collapsed` but not `enabled`) attributes those two leaves
to DIFFERENT layers; nothing is attributed to a layer that merely merged around the path.

**Probe:** `tests/config.test.ts:98-124` — home sets both moonshot_search fields → both
`"home"`; project sets only moonshot_fetch.enabled → `"project"`; env sets
maxCompletionTokens → `"env"`; runtime replace pins uploads.thresholdBytes → `"runtime"`;
untouched kimi_datasource → `"default"`. Executed GREEN this pass (config suite 12/12).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "buildSources sourceForPath hasPath KimiCodeConfigSources", limit: 5 });
// observed: all four symbols, total=4 — hasPath/buildSources tied #1, sourceForPath #3, interface #4
```
Adversarial note: the naive phrasing "effective field source attribution which layer set
value" MISSED this seam entirely in live retrieval (top-5 were shell scripts and UI
helpers) — retrieval requires the symbol vocabulary.

## Verdict
Adopt reverse-walk path probing over raw layers as the cheap way to produce a parallel
"provenance view" of any layered config. Adapt the sentinel vocabulary and decide whether
your UI needs leaf granularity (this one does, down to per-tool booleans). Omit only if
your layers are guaranteed total (every layer defines every field).
