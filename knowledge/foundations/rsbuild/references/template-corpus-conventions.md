<!-- capsule-v2 -->
# template corpus conventions — what must every framework template directory contain, and which per-framework deltas are contractual?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild`. **Question:** A porter maintaining a multi-framework template family needs the shared skeleton, the placeholder grammar, and the exact list of intentional per-framework divergences — so a missing file or a "normalized" difference doesn't slip in as an accident.

## Corpus layout
**Path/Symbol:** `packages/create-rsbuild/` — 21 `template-*/` dirs (vanilla/react/vue/lit/preact/svelte × js+ts, solid/solid2 × js+ts, octane × js+ts) + shared assets: `template-common/{AGENTS.md,README.md,gitignore,public/favicon.png}`, `template-tailwindcss/package.json`, `template-rstest/{AGENTS.md,<framework>-<lang>/ 4-file suites}`.
**Signature:** n/a — structural contract over static files.
**Data Shape:** every app template ships at minimum `package.json` + `rsbuild.config.(ts|js)` + `src/index.<ext>`; ts variants additionally ship `tsconfig.json`. Shared `gitignore` covers `.DS_Store *.local *.log* node_modules dist/ .rspack-profile-*/ .vscode/*` with the `!.vscode/extensions.json` un-ignore carve-out (only vue templates carry `.vscode/extensions.json`).

### Decisive source
```
# template-common/AGENTS.md — placeholders resolved by create-toolkit downstream
# {{ packageManager }} run dev - Start the dev server
# ...
- Rsbuild: https://rsbuild.rs/llms.txt
- Rspack: https://rspack.rs/llms.txt
```
```js
// template-lit-ts/rsbuild.config.ts — the two intentional legacy deltas
plugins: [pluginLit()],
html: { template: './src/index.html' },   // lit ships its own html shell
source: { decorators: { version: 'legacy' } }, // lit requires legacy decorators
```

**Flow:** toolkit copies `template-common/` into every scaffold, then the chosen `template-*`, then tool folders merge in (`rstest` suites, tailwindcss package.json).
**Invariant:** AGENTS.md files are TEMPLATES (`{{ packageManager }}`), never literal docs; rstest AGENTS.md additionally documents `test`/`test:watch` scripts that only exist after the rstest tool merges its package.json. Per-framework config deltas are contractual: lit = html template + legacy decorators; solid2 = pluginBabel(`/\.(?:jsx|tsx)$/`) + pluginSolid twin (plain solid uses pluginSolid alone); svelte templates alone carry `.browserslistrc`; react-ts alone carries `env.d.ts`; octane alone carries pnpm-workspace.yaml allowBuilds + .tsrx sources.
**Probe:** anchored at repo root: `grep -c 'packageManager }}' packages/create-rsbuild/template-common/AGENTS.md` → `3` (dev/build/preview commands); `grep -c 'packageManager }}' packages/create-rsbuild/template-rstest/AGENTS.md` → `2` (test/test:watch) = `5` placeholder sites; `ls packages/create-rsbuild/template-svelte-ts/.browserslistrc packages/create-rsbuild/template-react-ts/src/env.d.ts` → both exist (svelte-only browserslist, react-ts-only env.d.ts).
**Probe (static):** `ls packages/create-rsbuild | grep -c '^template-'` → `21`; `cat packages/create-rsbuild/template-vanilla-js/rsbuild.config.js` → ends with `export default defineConfig({});` (the empty-config baseline the rewrite kernel's seed path targets).

Direct tests pin the deltas indirectly via tools.test.ts lit-ts snapshot (:114-144 asserts BOTH the html.template and legacy decorators blocks survive plugin insertion).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "create rsbuild template common agents", limit: 5 });
```
Live-resolved 2026-08-24 at `2bcf61c`: resolves the `packages.create-rsbuild` Module/File nodes for the cited paths. Caveat: static asset files are content-only nodes — grep is authoritative for their bodies.

## Verdict
Adopt the minimum-skeleton rule, the placeholder-in-docs pattern, and the gitignore un-ignore carve-out; treat listed per-framework deltas as CONTRACT (tests snapshot them). Adapt the framework roster and file inventories to your host. Omit favicon binary and README prose content. Caveat: no test enumerates the corpus itself — the 21-dir census is my sweep evidence at this pin, not upstream-pinned.
