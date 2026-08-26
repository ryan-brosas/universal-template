<!-- capsule-v2 -->
# Layered config merge ladder — how do you layer defaults/home/project/env/runtime config without mutating shared defaults or persisting ad-hoc overrides?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** A provider extension needs user config from four origins (global file, project file, env vars, in-session overrides) over built-in defaults — what is the merge order, the merge semantics, and where do per-call overrides live?

## Layered config merge ladder
**Path/Symbol:** `src/config.ts:489-523` (`loadLayers`, `loadKimiCodeConfig`); merge kernel `mergeConfigPatch` :210-225; defaults `DEFAULT_KIMI_CODE_CONFIG` :113-135; per-call overrides parameter `LoadKimiCodeConfigOptions`/`overrides?` :511-514; production caller `reloadEffectiveKimiRuntimeConfig` index.ts:129-150.
**Signature:** `loadLayers(options): Array<{source: KimiConfigSource; config: Record<string, unknown>}>`; `mergeConfigPatch<T extends Record<string, unknown>>(base: T, patch: Record<string, unknown>): T`; `loadKimiCodeConfig(options, overrides?): KimiCodeConfig`.
**Data Shape:** layers are `{source: "home"|"project"|"env"|"runtime", config}` pairs merged onto a fresh deep clone of the default config; patches use `unknown` field types (`KimiCodeConfigPatch`) because raw layers are unvalidated until the final validate step.

### Decisive source
```ts
export function loadKimiCodeConfig(
  options: LoadKimiCodeConfigOptions,
  overrides?: KimiCodeConfigPatch,
): KimiCodeConfig {
  let merged = clone(DEFAULT_KIMI_CODE_CONFIG) as unknown as Record<string, unknown>;
  for (const layer of loadLayers(options)) {
    merged = mergeConfigPatch(merged, layer.config);
  }
  if (overrides) {
    merged = mergeConfigPatch(merged, overrides as Record<string, unknown>);
  }
  return validateKimiCodeConfig(merged);
}
```
```ts
const result: Record<string, unknown> = { ...base };
for (const [key, value] of Object.entries(patch)) {
  if (value === undefined) continue;
  const current = result[key];
  if (isRecord(current) && isRecord(value)) {
    result[key] = mergeConfigPatch(current, value);
  } else {
    result[key] = value;
  }
}
```
And the layer order itself (`loadLayers` :492-507): home first, then project **only when
`options.includeProject !== false`**, then env, then runtime — so precedence is
defaults → home → project → env → runtime, and the per-call `overrides` patch sits above
every layer without ever being written into module state or disk.

**Flow:** clone defaults → fold each layer through `mergeConfigPatch` (recursive on nested
records only; leaves replace; `undefined` values are skipped so a layer can express "no
opinion") → apply the ephemeral call-scoped overrides → run the whole merged blob through
`validateKimiCodeConfig`. The production extension re-runs this on every cwd change /
trust change (`applyEffectiveKimiRuntimeConfig`, index.ts:152-161), passing its session's
`state.overrides` as the per-call argument rather than touching the runtime-override trio.
**Invariant:** `DEFAULT_KIMI_CODE_CONFIG` is never mutated (cloned per call via JSON
round-trip); a lower layer can never override a higher one regardless of key shape;
validation happens once at the end so every layer stays raw/typed-`unknown` until merge
completes; per-call overrides vanish with the call — nothing persists them.

**Probe:** `tests/config.test.ts:69-96` — home sets `maxTokens:16000`, project sets
`24000` (wins), env sets `KIMI_MODEL_MAX_COMPLETION_TOKENS:"32000"` but the runtime
override's `64000` wins; asserts all four interactions in one loaded config. Executed
GREEN this pass: `node --test tests/config.test.ts` → 12/12 pass at pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "merge home project env runtime config priority layers", limit: 5 });
// observed: loadLayers #1 (-21.51), mergeConfigPatch #2 (-20.8)
```

## Verdict
Adopt the five-source ladder with an explicit source tag per layer and a final
validate-after-merge step; adopt "undefined means no opinion" as the patch vocabulary.
Adapt layer names/paths to your host and decide deliberately whether your equivalent of
the project layer should be trust-gated (here it is, via includeProject). Omit the
per-call overrides channel only if your overrides are genuinely global.
