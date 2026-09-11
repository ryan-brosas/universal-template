<!-- capsule-v2 -->
# react-compiler config surgery — how is `pluginReact()` upgraded to `pluginReact({ reactCompiler: true })` in place, and what happens on a second run?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild`. **Question:** A porter adding an "enable option X inside an existing plugin call" feature must know the exact textual patterns matched, the precedence between single-line and multi-line forms, and the failure mode when the rewrite runs twice against different write paths.

## The upgrade function
**Path/Symbol:** `packages/create-rsbuild/src/rsbuildConfig.ts:78-102` (`addReactCompilerOption`), exported via `enableReactCompilerInRsbuildConfig` :207-216 (read current file → normalize CRLF → write result; NO cache participation).
**Signature:** `addReactCompilerOption(code: string): string` — throws `Error('Failed to update rsbuild.config: pluginReact call not found.')` if neither pattern matched.
**Data Shape:** Input/output are whole-file strings. Two target shapes: single-line `plugins: [pluginReact()]` (regex form) and multi-line `  plugins: [` … `    pluginReact(),` (literal form).

### Decisive source
```ts
const reactCompilerCall = `pluginReact({
  reactCompiler: true,
})`;
const multiLineCall = `${indent}${indent}pluginReact(),`;
const replaceCall = (call) => (call === 'pluginReact()' ? reactCompilerCall : call);
const next = code
  .replace(/^ {2}plugins: \[(.*pluginReact\(\).*)\],$/m, (_, calls) =>
    formatPlugins(calls.split(', ').map(replaceCall)),
  )
  .replace(multiLineCall, formatCall(reactCompilerCall));
if (next !== code) return next;
throw new Error('Failed to update rsbuild.config: pluginReact call not found.');
```

**Flow:** try single-line regex first — anchored `^ {2}plugins: [...]$`, requires `pluginReact()` INSIDE the brackets, splits calls on `, `, replaces ONLY exact `pluginReact()` tokens, re-renders via `formatPlugins` (so one plugin stays single-line, two go multi-line). Else replace literal `\n    pluginReact(),` with the formatted multi-line compiler call. No change ⇒ throw.
**Invariant:** The regex's `^ {2}` + `/m` anchor means the pattern matches only top-level `defineConfig` bodies at exactly two-space indent. The literal multi-line arm uses `${indent}${indent}` = 4 spaces of body indent. Guard `code.includes('reactCompiler:')` makes direct reruns idempotent.

**HAZARD — CORRECTED BY INDEPENDENT AUDIT EXECUTION (2026-08-24, post-commit `da7ea142`; four node type-strip executions against live source):** the original draft mis-stated the trigger and missed the more dangerous second mode.
1. **Duplicate upgrade** requires a base config that ALREADY contains bare `pluginReact()` (e.g. a react-template scaffold). Root cause: `addImport` dedupes by `code.includes(plugin.source)`, but `addCalls` NEVER dedupes call expressions — so adding a ConfigPlugin whose call already exists appends a SECOND identical call (`[pluginReact(), …, pluginReact()]`). Executed (base with `plugins: [pluginReact()]`, then tw→rc→enable): final array = two `pluginReact({ reactCompiler: true })` + one `pluginTailwindcss()` (reactCompiler occurrences: 2) — enable's exact-token `replaceCall` upgrades EVERY bare instance in the split-calls list.
2. **Silent revert** (no throw, the dangerous mode): any LATER same-process `addPluginsToRsbuildConfig` call after an `enableReactCompilerInRsbuildConfig` write REGENERATES from the cache's pre-enable base snapshot and DROPS the flag entirely. Executed (tw→enable→lit): final output `plugins: [pluginReact(), pluginLit(), pluginTailwindcss()]`, reactCompiler occurrences: 0. The compiler flag lives outside the cache's world; regeneration silently un-does it.
3. **Designed loud failure**: `enableReactCompilerInRsbuildConfig` on a config with NO `pluginReact()` at all (e.g. vanilla scaffold after tw) throws `Error('Failed to update rsbuild.config: pluginReact call not found.')` at :99 — executed. On a plain empty-config base WITHOUT pre-existing pluginReact, the claimed tw→rc→enable sequence yields exactly ONE correctly-upgraded call + tailwind, no duplication (executed) — the single bare token rc appended is the only one enable ever sees.
Porter obligation: route every mutation through ONE cache-owned path and treat the direct-path `enable*` function as terminal (never followed by another `addPluginsToRsbuildConfig` in the same process).
**Probe (behavioral — executed GREEN 2026-08-24):** from `packages/create-rsbuild/src/`,
`node -e "import('./rsbuildConfig.ts').then(async m => { await m.enableReactCompilerInRsbuildConfig('/tmp/rsbpass4_b'); })"` where `/tmp/rsbpass4_b/rsbuild.config.js` holds single-line `plugins: [pluginReact()]` produces exactly:
```js
export default defineConfig({
  plugins: [
    pluginReact({
      reactCompiler: true,
    }),
  ],
});
```
matching upstream snapshot `e2e/cases/create-rsbuild/tools.test.ts:258-267` (inside the `:240-268` test).
**Probe (static):** anchored at the repo root: `grep -n 'reactCompiler:' packages/create-rsbuild/src/rsbuildConfig.ts` → `79` and `84` (guard + template); `grep -cF 'pluginReact()' packages/create-rsbuild/src/rsbuildConfig.ts` → `2` (replaceCall comparison + multiLine literal context).
**HAZARD PROVEN BY EXECUTION (adversarial RED/GREEN):** running tailwind via `addPluginsToRsbuildConfig('/tmp/rsbpass4_c', ...)` FIRST, then `addPluginsToRsbuildConfig(...,[pluginReact])` + `enableReactCompilerInRsbuildConfig(...)` on the SAME dir produced `pluginReact({reactCompiler:true})` TWICE in the array — because the second `addPluginsToRsbuildConfig` regenerated from its own base snapshot (captured AFTER tailwind but BEFORE the compiler write) and then the direct-path compiler upgrade ALSO ran on the live file. In the shipped CLI each tool action runs once per process, so this needs a custom multi-tool host to trigger; porters embedding these functions MUST route every mutation through ONE cache-owned path or accept duplicate-plugin corruption.

Direct tests pin both orderings end-to-end through the real binary: `tools.test.ts:240-268` (`[react-compiler]` snapshot), `:269-299` (`[react-compiler, tailwindcss]` → compiler-upgraded React + tailwind after), `:300-330` (`[tailwindcss, react-compiler]` → IDENTICAL output proving sort-based reorder), `:331-347` (`when` gate ignores the tool for vanilla and leaves config untouched).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "enableReactCompilerInRsbuildConfig reactCompiler pluginReact", limit: 3 });
```
Live-resolved 2026-08-24 at `2bcf61c`: rank#2 `...rsbuildConfig.enableReactCompilerInRsbuildConfig Function ... 207-216` line-exact (rank#1 was `plugin-react/src/pluginReact` itself — expected cross-package hit; adjudicated correct).

## Verdict
Adopt the two-shape match grammar, exact-token replacement (only bare `pluginReact()` upgrades), guard-first idempotence, and the loud not-found error. Adapt the concrete plugin/option names freely. Omit nothing — formatting IS the contract here. Caveat: the double-write hazard is documented by my own execution evidence, NOT pinned by upstream tests; treat it as a porter obligation, not an upstream bug.
