<!-- capsule-v2 -->
# rsbuildConfig.ts config-rewrite kernel — how do you add plugins to a generated `rsbuild.config` file textually, idempotently, and in deterministic order?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild`. **Question:** A porter implementing "add a plugin to an existing config file" as TEXT EDITING (not AST) must reproduce the exact single-line vs multi-line grammar, the import-insertion anchor, the empty-object seed path, and the regenerate-from-base cache — otherwise edits corrupt configs or duplicate plugins.

## The rewrite engine
**Path/Symbol:** `packages/create-rsbuild/src/rsbuildConfig.ts:1-216` — `ConfigPlugin` type :4-11, `tailwindcssPlugin` const :13-18 (`order: 20`), `cache` Map :28, `normalize` CRLF→LF :32, `getCall` :34-35 (`call ?? `${importName}()`), `addImport` :37-53, `formatCall` :55-63 (4-space body indent via `${indent}${indent}` where `indent='  '`), `formatPlugins` :65-76 (single-line iff NO call contains `\n`), `addReactCompilerOption` :78-102, `addPluginsField` :104-124, `addCalls` :126-157, `applyPlugins` :159-167 (imports first for ALL plugins, then calls once), `findConfig` :169-173 (ts before js), `addPluginsToRsbuildConfig` :175-205, `enableReactCompilerInRsbuildConfig` :207-216.
**Signature:** `addPluginsToRsbuildConfig(dir: string, plugins: ConfigPlugin[]): Promise<void>`; `enableReactCompilerInRsbuildConfig(dir: string): Promise<void>`; `ConfigPlugin = { id, importName, source, importLine?, call?, order? }`.
**Data Shape:** Per-dir `ConfigState = { file, base, plugins: Map<id, ConfigPlugin> }` cached module-level (:28). `base` is the ORIGINAL file content captured on first call — every subsequent call re-applies ALL accumulated plugins to `base`, never to prior output.

### Decisive source
```ts
// Tool actions may update the same config file one after another. Keep the
// original config and regenerate from it so plugin order stays deterministic.
const cache = new Map<string, ConfigState>();
```
```ts
// Reapply every selected plugin to the original config on each call. This
// avoids appending to previously generated code when multiple tools are used.
const ordered = [...state.plugins.values()].sort(
  (a, b) => (a.order ?? 0) - (b.order ?? 0),
);
await fs.promises.writeFile(state.file, applyPlugins(state.base, ordered));
```

**Flow (single-line array):** `addCalls` finds the line containing `plugins: [`; if that trimmed line ends with `],`, it regex-extracts `/^plugins: \[(.*)\],$/` and rewrites the WHOLE line via `formatPlugins([...oldCalls, ...newCalls])`.
**Flow (multi-line array):** if the `plugins: [` line doesn't end with `],`, find the first later line trimming exactly to `],` and SPLICE formatted calls BEFORE it (:145-155).
**Flow (no plugins field):** empty-seed `defineConfig({});` is string-replaced with `defineConfig({\n<formatted plugins>\n});` (:104-110); otherwise insert after `'export default defineConfig({\n'` (:112-115); neither match ⇒ loud `Error('Failed to update rsbuild.config: defineConfig object not found.')`.
**Flow (imports):** `addImport` skips if `code.includes(plugin.source)` already present, else splices after the LAST line starting with `import ` (`lines.findLastIndex(...)` :43).
**Invariant:** Idempotence + determinism come ONLY from the {base snapshot + id-keyed Map + order-sort} trio; any write path that bypasses the cache (e.g. calling `enableReactCompilerInRsbuildConfig`, which reads/writes the CURRENT file directly) breaks regeneration — see hazard below. `formatCall` prefixes each call-body line with `${indent}${indent}` = 4 literal spaces (two 2-space `indent` units concatenated), comma only on the last line — so inside a top-level `  plugins: [` array the call lines render as `    pluginReact(),` (4 leading spaces), matching upstream snapshots.
**Probe (behavioral, node ≥23 type-stripping — executed GREEN 2026-08-24 from `packages/create-rsbuild/src/`):**
`node -e "import('./rsbuildConfig.ts').then(async m => { await m.addPluginsToRsbuildConfig('/tmp/rsbpass4_a', [{id:'tw',importName:'pluginTailwindcss',source:'@rsbuild/plugin-tailwindcss',order:20}]); })"` on a fixture containing `export default defineConfig({});` produces:
```js
export default defineConfig({
  plugins: [pluginTailwindcss()],
});
```
byte-equal to upstream snapshot `e2e/cases/create-rsbuild/tools.test.ts:60-67`.
**Probe (static):** anchored at the repo root: `grep -n 'Reapply every selected' packages/create-rsbuild/src/rsbuildConfig.ts` → `198`; `grep -n 'order ?? 0' packages/create-rsbuild/src/rsbuildConfig.ts` → `201`; `grep -n 'defineConfig({});' packages/create-rsbuild/src/rsbuildConfig.ts` → `105`,`107`; `grep -n 'findLastIndex' packages/create-rsbuild/src/rsbuildConfig.ts` → `43`.

Direct tests: `e2e/cases/create-rsbuild/tools.test.ts:43-72` (vanilla tailwind exact-config snapshot incl. `// @ts-check` header preserved), `:73-102` (react + tailwind two-plugin single-line form), `:103-135` (lit-ts multi-field config keeps `html.template`/`source.decorators` while plugins inserted after `defineConfig({`), `:269-330` ORDER-INDEPENDENCE pair (`[react-compiler, tailwindcss]` vs `[tailwindcss, react-compiler]` produce IDENTICAL snapshots).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "addPluginsToRsbuildConfig config plugin cache", limit: 5 });
```
Live-resolved 2026-08-24 at `2bcf61c`: rank#1 `...create-rsbuild.src.rsbuildConfig.addPluginsToRsbuildConfig Function ... 175-205` line-exact (true post-reindex span). Companion retrieves: `addCalls plugins array insert closing bracket` → rank#1 `addCalls ... 126-157`.

## Verdict
Adopt the whole engine as one unit: base-snapshot regeneration, id-keyed accumulation, `(order ?? 0)` stable sort, ts-before-js file ladder, CRLF normalize, last-import splice anchor, single/multi-line duality with the ends-with-`],` discriminator, empty-config seed replacement, and the loud not-found errors (never silent no-op on malformed configs — EXCEPT missing config file which returns silently so tools stay optional). Adapt `indent`/formatting to your host style. Omit nothing internal — the formatting details ARE the snapshot contract. Caveat: behavioral probe requires node ≥23 type-stripping or transpile; no vitest/jest suite covers this file directly.
