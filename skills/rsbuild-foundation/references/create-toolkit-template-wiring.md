<!-- capsule-v2 -->
# create-rsbuild template wiring — how does the CLI bind framework templates, aliases, and optional tools/skills onto the external `create()` kernel?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild`. **Question:** A porter adding a framework template to an Rsbuild-style scaffolder must know exactly which strings are load-bearing where — the directory name, the CLI `-t` value, the interactive label, the alias map, and the tool/skill hooks — or the template silently becomes unreachable.

## Template registry + name resolution
**Path/Symbol:** `packages/create-rsbuild/src/index.ts:18-60` (`frameworkAlias`, `getTemplateName`) and `src/index.ts:109-216` (`create({...})` wiring). Top-of-file imports bind `create/copyFolder/checkCancel/select` from the EXTERNAL package `@rstackjs/create-toolkit` (pinned `2.2.4` in the root `pnpm-lock.yaml`; not vendored in this repo).
**Signature:** `async function getTemplateName({ template }: Argv): Promise<string>`; `create({ root, name, templates: string[], getTemplateName, mapESLintTemplate, mapRslintTemplate, extraTools: ExtraTool[], extraSkills: ExtraSkill[] })`.
**Data Shape:** `template` CLI value grammar is `framework[-language]`: `template.split('-')`, `pair[0]` = framework, `pair[1] ?? 'js'` (language DEFAULTS TO js when omitted — `createAndValidate(dir,'octane')` resolves `octane-js`). Alias map normalizes legacy names BEFORE directory lookup: `{ vue3: 'vue', 'solid-js': 'solid' }`. Returned `${framework}-${language}` MUST equal a directory `packages/create-rsbuild/template-<name>/` AND a member of the `templates:` array — the array is duplicated state with the filesystem (21 dirs `template-*`, 17 listed in `templates:` plus `tailwindcss` which is tool-only).

### Decisive source
```ts
const frameworkAlias: Record<string, string> = {
  vue3: 'vue',
  'solid-js': 'solid',
};

async function getTemplateName({ template }: Argv) {
  if (typeof template === 'string') {
    const pair = template.split('-');
    const language = pair[1] ?? 'js';
    const framework = pair[0];
    return `${frameworkAlias[framework] ?? framework}-${language}`;
  }
  // interactive path: two select() prompts, values 'vanilla'|'react'|...|'octane'
  // then 'ts'|'js'; labels carry marketing only ('Solid 1'/'Solid 2' as of 2bcf61c)
```

**Flow:** CLI `-t <name>` → split/alias/`?? 'js'` → `template-<resolved>` folder copied by toolkit into user dist → else two `select()` prompts build the same string. After copy, selected `extraTools` run (each `action({ templateName, distFolder, addAgentsMdSearchDirs })` or `command` string), then `extraSkills` filter by `when`.
**Invariant:** The interactive prompt VALUES, the CLI grammar, and the `templates:` array entries must resolve to the same `template-*` directory set; renaming a value without moving/renaming the directory breaks both paths. Prompt labels are display-only (commit 2bcf61c relabeled `Solid`→`Solid 1`, `Solid 2 (RC)`→`Solid 2` and moved octane after solid2 — zero behavior change).
**Probe:** anchored at the repo root: `grep -n 'frameworkAlias' packages/create-rsbuild/src/index.ts` → lines `18` (map declared before any use) and `29` (lookup with `?? framework` fallback); `ls packages/create-rsbuild | grep -c '^template-'` → `21`.

Direct tests pin the whole grammar end-to-end through the published binary: `e2e/cases/create-rsbuild/helper.ts` runs `node CREATE_RSBUILD_BIN_PATH <name> -t <template>` and asserts `scripts.dev === 'rsbuild'`, `scripts.build === 'rsbuild build'` (vue overrides `'vue-tsc && rsbuild build'`), `@rsbuild/core` present, and tsconfig existence iff `-ts`; alias cases `vue3`/`vue3-ts` assert identical outcomes to `vue`/`vue-ts` (jsTemplates.test.ts / tsTemplates.test.ts / basic.test.ts sub-dir creation).

## Tool/skill hook surface
**Path/Symbol:** `packages/create-rsbuild/src/index.ts:135-215`.
**Signature:** `ExtraTool = { value, label, order?: 'pre', when?: (ctx) => boolean, action?: (ctx) => void|Promise<void>, command?: string }`; ctx carries `{ templateName, distFolder, addAgentsMdSearchDirs, tools }`.
**Data Shape:** `rstest` copies `template-rstest/<mapRstestTemplate(name)>` with `copyFolder(..., { isMergePackageJson: true })` and registers `addAgentsMdSearchDirs(toolFolder)` so the copied `AGENTS.md` joins agent-doc discovery; `storybook` is the pure-`command` form (`npm create storybook@latest -- --skip-install --features docs`). `extraSkills` entries reference remote skill repos (`rstackjs/agent-skills`, `vercel-labs/agent-skills`) gated by `tools.includes('rstest')` / `templateName.startsWith('react-')`.
**Flow:** template copy → `order:'pre'` tools (rstest, react-compiler) → normal tools (tailwindcss) → `command` tools (storybook) → skill install filtered by final templateName/tools.
**Invariant:** Tools that merge into `package.json` MUST pass `isMergePackageJson: true` or they clobber the scaffolded manifest; `{{ packageManager }}` placeholders inside `template-common/AGENTS.md` / `template-rstest/AGENTS.md` are resolved downstream by the toolkit, so AGENTS.md text is a template, not literal docs.
**Probe:** `grep -n '      order:' packages/create-rsbuild/src/index.ts` → exactly `139` and `156` (the two `'pre'` tools); `grep -c 'isMergePackageJson' packages/create-rsbuild/src/index.ts` → `2` (rstest + tailwindcss actions only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "getTemplateName frameworkAlias template select", limit: 5 });
```
Live-resolved 2026-08-24 at `2bcf61c`: rank#1 `packages.create-rsbuild.src.getTemplateName Function packages/create-rsbuild/src/index.ts 23-60` line-exact.

## Verdict
Adopt the three-way identity contract (CLI value ≡ prompt value ≡ directory/array entry), the `split('-')` + `?? 'js'` default grammar, and the alias-normalize-before-lookup pattern; adopt `extraTools` action/command duality and `isMergePackageJson` merge discipline. Adapt the toolkit boundary (`@rstackjs/create-toolkit` supplies create/select/copy primitives — substitute your own scaffolder kernel). Omit npm-publish packaging metadata and the concrete framework roster. Caveat: no unit tests exist for `getTemplateName` itself — the grammar is pinned only through e2e binary runs.
