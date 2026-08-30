<!-- capsule-v2 -->
# tailwindcss tool action — how does a scaffolder inject BOTH a config plugin and a CSS import, and why does it probe two filenames?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild`. **Question:** A porter implementing "add styling to the scaffold" must reproduce the dual mutation (package.json merge + CSS prepend + plugins-array insert) and the first-existing-file probe that makes it template-agnostic.

## The tool action
**Path/Symbol:** `packages/create-rsbuild/src/index.ts:163-190` (tailwindcss entry in `extraTools`); plugin descriptor `tailwindcssPlugin` at `src/rsbuildConfig.ts:13-18` (`{ id: 'tailwindcss', importName: 'pluginTailwindcss', source: '@rsbuild/plugin-tailwindcss', order: 20 }`).
**Signature:** `action: async ({ distFolder }) => { ... }` — no `order` field ⇒ runs in default phase AFTER `'pre'` tools.
**Data Shape:** `mainCssFile = ['index.css', 'App.css']` probe list; prepend payload `@import 'tailwindcss';\n\n`; `copyFolder({ from: template-tailwindcss/, to: distFolder, isMergePackageJson: true })`.

### Decisive source
```ts
const mainCssFile = ['index.css', 'App.css'];
for (const cssFile of mainCssFile) {
  const filePath = path.join(distFolder, 'src', cssFile);
  if (fs.existsSync(filePath)) {
    const content = await fs.promises.readFile(filePath, 'utf-8');
    await fs.promises.writeFile(
      filePath,
      `@import 'tailwindcss';\n\n${content}`,
    );
    break;
  }
}
await addPluginsToRsbuildConfig(distFolder, [tailwindcssPlugin]);
```

**Flow:** copy `template-tailwindcss/` into dist (merging devDeps into package.json) → probe `src/index.css` then `src/App.css`, prepend the Tailwind v4-style `@import` to the FIRST existing file and STOP (`break`) → register the plugin via the text-rewrite kernel (see `config-text-rewrite-kernel`).
**Invariant:** Exactly one CSS file gets the import — vanilla templates ship `index.css`, component templates ship `App.css`; the ORDER of the probe list is the tie-break. The `break` is load-bearing: prepending twice would double-import. `order: 20` on the descriptor is why tailwind lands AFTER react-compiler in every snapshot regardless of CLI flag order.
**Probe:** anchored at repo root: `grep -n "mainCssFile = \['index.css', 'App.css'\]" packages/create-rsbuild/src/index.ts` → line `175`; `grep -n 'break;' packages/create-rsbuild/src/index.ts` → line `184` inside this action; `grep -n 'order: 20' packages/create-rsbuild/src/rsbuildConfig.ts` → line `17`.

Direct tests pin all three mutations with exact snapshots: `e2e/cases/create-rsbuild/tools.test.ts:43-72` (vanilla: css import in `src/index.css` + single-plugin config snapshot at `:60-67`), `:73-102` (react: `App.css` chosen + `plugins: [pluginReact(), pluginTailwindcss()]`), `:103-135` (lit-ts: multi-field config preserved). `tools.test.ts:54-55` also pins the negative: `@tailwindcss/postcss` must be ABSENT (template carries the v4 import style, not the legacy postcss plugin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "addPluginsToRsbuildConfig tailwindcss order", limit: 5 });
```
Live-resolved 2026-08-24 at `2bcf61c`: rank#1 `...rsbuildConfig.addPluginsToRsbuildConfig Function ... 175-205` (the callee — the action itself is an inline closure, reachable through its callsite; static grep remains authoritative for :163-190).

## Verdict
Adopt the first-existing-file prepend-and-break pattern for template-agnostic CSS injection, the isMergePackageJson manifest merge, and order-tagged plugin descriptors so multi-tool compositions stay deterministic. Adapt filenames/probe lists to your template corpus. Omit the storybook `command`-style tool (external npx UX, not portable).
