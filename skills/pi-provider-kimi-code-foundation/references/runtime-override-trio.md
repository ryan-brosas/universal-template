<!-- capsule-v2 -->
# Runtime override trio — how do you give embedded hosts ephemeral config control without touching disk, and who actually uses it?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** How do you expose set/replace/clear semantics over a module-global config patch safely — and is a global patch even the right production channel?

## Runtime override trio
**Path/Symbol:** `src/config.ts:137-153` (`runtimeOverride`, `setRuntimeKimiCodeConfigOverride`, `replaceRuntimeKimiCodeConfigOverride`, `clearRuntimeKimiCodeConfigOverride`, `getRuntimeKimiCodeConfigOverride`); merge kernel `mergeConfigPatch` :210-225; clone :167-169. Production alternative: index.ts:129-137 (`reloadEffectiveKimiRuntimeConfig` passes per-call overrides instead).
**Signature:** all four are `void`/`KimiCodeConfigPatch` synchronous functions over one module-global `let runtimeOverride: KimiCodeConfigPatch = {}`.
**Data Shape:** the global holds only a *patch* (`Partial` tree with `unknown` leaves), never a full config; it participates in the ladder as the highest layer.

### Decisive source
```ts
let runtimeOverride: KimiCodeConfigPatch = {};

export function setRuntimeKimiCodeConfigOverride(patch: KimiCodeConfigPatch): void {
  runtimeOverride = mergeConfigPatch(runtimeOverride, patch);
}

export function replaceRuntimeKimiCodeConfigOverride(patch: KimiCodeConfigPatch): void {
  runtimeOverride = patch;
}

export function clearRuntimeKimiCodeConfigOverride(): void {
  runtimeOverride = {};
}

export function getRuntimeKimiCodeConfigOverride(): KimiCodeConfigPatch {
  return clone(runtimeOverride) as KimiCodeConfigPatch;
}
```

**Flow:** `set` deep-merges the argument into the accumulated patch (so repeated sets
compose instead of clobbering); `replace` swaps wholesale (test harnesses use it to pin
exactly one override); `clear` resets to `{}`; the getter returns a JSON deep clone so
callers can inspect but not mutate live state. The patch reaches effect only inside
`loadLayers` (config.ts:506) as the final layer of `loadKimiCodeConfig`.
**Invariant:** the trio mutates process-global state with no ownership/lifetime tracking —
which is precisely why production does NOT use it. Adjudication at this pin:
`trace_path` inbound for both setter and getter returns callers_total=0, and checkout grep
finds references only in tests/config.test.ts (:82/:94 use set+clear;
:109/:122 use replace+clear). The extension threads session-scoped patches through
`loadKimiCodeConfig(options, state.overrides)` (index.ts:134-137) so overrides die with
the session instead of leaking across sessions in the same process.
**Invariant (tests):** every test that touches the trio restores state in `finally { clear... }`
— the minimum hygiene any adopter must copy.

**Probe:** `tests/config.test.ts:82-95` — set accumulates `{model.generation.maxCompletionTokens:64000}` above env's 32000, cleared in finally; :109-123 — replace pins `uploads.thresholdBytes:2048` and sources report `"runtime"`. Executed GREEN this pass (`node --test tests/config.test.ts` 12/12).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "runtime override patch set replace clear", limit: 5 });
// observed: replace #1, clear #2, set #3, get #4 (all three setters + getter, total 19)
```

## Verdict
Adopt the three-verb vocabulary (merge-in / swap / reset) plus clone-on-read whenever you
must expose an override surface to tests or embedders. Adapt by preferring the per-call
overrides parameter as your production channel and reserving the global trio for test
harnesses — this repo's own evolution is the evidence. Omit the global entirely if your
host is single-session.
