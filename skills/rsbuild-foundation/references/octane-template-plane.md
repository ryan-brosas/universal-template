<!-- capsule-v2 -->
# Octane template plane — what does a first-class third-party-framework template require beyond a config file, and why does `.tsrx` exist?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5` (introduced `bc19fd5` #8349, reordered `2bcf61c` #8353); Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild`. **Question:** A porter adding an SSR/JSX-dialect framework template must know which pieces are load-bearing (file extension, render syntax, pnpm build-script allowlist) vs cosmetic — miss one and the scaffolded project fails at install or compile.

## The template corpus
**Path/Symbol:** `packages/create-rsbuild/template-octane-{js,ts}/` whole trees; sibling templates `template-solid2-ts/` (babel+pluginSolid twin), `template-lit-ts/` (html.template + legacy decorators), `template-vanilla-js/` (the empty-config baseline).
**Signature:** n/a — static scaffold; the contract is the file SET plus package.json fields.
**Data Shape:** octane-ts `package.json`: dependency `octane ^0.1.44`; devDeps `@octanejs/rsbuild-plugin ^0.1.39`, `@rsbuild/core ^2.2.0-beta.2`, `@tsrx/typescript-plugin ^0.3.124`, `typescript ^5.9.3`; script `typecheck: "tsrx-tsc --noEmit -p tsconfig.json"`. `pnpm-workspace.yaml` carries ONLY `allowBuilds:\n  esbuild: true`. Source files: `src/index.ts` (`createRoot(rootEl).render(App)` from `'octane'`) + `src/App.tsrx`.

### Decisive source
```tsx
// template-octane-ts/src/App.tsrx  — note the .tsrx extension and @{ } body
import './App.css';

export function App() @{
  <div class="content">
    <h1>Rsbuild with Octane</h1>
    <p>Start building amazing things with Rsbuild.</p>
  </div>
}
```
```ts
// rsbuild.config.ts — plugin owns the dialect; no babel in sight
import { defineConfig } from '@rsbuild/core';
import { pluginOctane } from '@octanejs/rsbuild-plugin';

export default defineConfig({
  plugins: [pluginOctane()],
});
```

**Flow:** user picks octane → toolkit copies `template-octane-<lang>` → pnpm install runs esbuild's postinstall → `allowBuilds: esbuild: true` is what permits it under pnpm's build-scripts gate → `rsbuild dev/build` delegates JSX/TSX dialect handling to `pluginOctane()`.
**Invariant:** A `.tsrx` file with `@{ }` component bodies is NOT valid TS/JSX for any stock toolchain — it compiles only because `@octanejs/rsbuild-plugin` claims the extension. Porters must carry THREE coupled facts together: the extension, the syntax, and the owning plugin. The pnpm `allowBuilds` stanza is load-bearing for install (esbuild binary download), not decoration.
**Probe:** anchored at the repo root: `ls packages/create-rsbuild | grep -c '^template-octane'` → `2`; `grep -c '@{' packages/create-rsbuild/template-octane-ts/src/App.tsrx` → `1`; `grep -ci tsrx packages/create-rsbuild/template-octane-ts/package.json` → `2` (`tsrx-tsc` script + `@tsrx/typescript-plugin`).

Direct tests: `e2e/cases/create-rsbuild/jsTemplates.test.ts:11-16` asserts `pkgJson.dependencies.octane` AND `devDependencies['@octanejs/rsbuild-plugin']` truthy after a real binary run with `-t octane`; `tsTemplates.test.ts:11-17` adds `@tsrx/typescript-plugin` for `-t octane-ts`. These are the only behavioral pins of the plane.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "create octane project expected", limit: 5 });
```
Live-resolved 2026-08-24 at `2bcf61c`: rank#1 = the octane e2e test node in `e2e/cases/create-rsbuild/tsTemplates.test.ts` (line-exact). Caveat: static template files are content, not symbols — grep is the authoritative retrieval for `.tsrx`/package.json bodies; the graph indexes them as file nodes only.

## Verdict
Adopt the coupling rule (extension+syntax+owner-plugin travel as one unit) and the pnpm allowBuilds requirement when scaffolding any toolchain whose installer needs build scripts. Adapt the concrete versions/plugin names to your target framework. Omit marketing labels ('Octane' prompt entry) and docs-site registration (quick-start.mdx table row). Caveat: templates have NO direct unit tests; behavior is pinned only via the two e2e create-and-inspect-package.json tests.
