<!-- capsule-v2 -->
# create-rsbuild e2e harness — how do you behaviorally test a scaffolder CLI without installing anything?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild`. **Question:** A porter testing a project generator must know the exec-and-inspect harness pattern: how templates are invoked, what invariants every scaffold must satisfy, and how exact-config snapshots make textual formatting part of the tested contract.

## The harness
**Path/Symbol:** `e2e/cases/create-rsbuild/helper.ts` (`expectPackageJson` :7-16, `createAndValidate` :18-71); suites `basic.test.ts`, `jsTemplates.test.ts`, `tsTemplates.test.ts`, `tools.test.ts`.
**Signature:** `createAndValidate(cwd, template, { name?, tools?, clean?, expectedBuildScript? }): Promise<{ dir, pkgJson, clean }>` — shells out via `node:child_process.exec('node CREATE_RSBUILD_BIN_PATH <name> -t <template> [--tools <t> ...]')`, then reads `<dir>/package.json`.
**Data Shape:** `CREATE_RSBUILD_BIN_PATH` imported from `@e2e/helper` (the built package bin); per-template assertions live IN THE SUITES, not the helper. Windows CRLF is normalized before comparison (`readCreatedFile` replaces `\r\n` → `\n`) so generated fixtures match LF snapshots cross-platform.

### Decisive source
```ts
export const expectPackageJson = (
  pkgJson: Record<string, any>,
  name: string,
  expectedBuildScript = 'rsbuild build',
) => {
  expect(pkgJson.name).toBe(name);
  expect(pkgJson.scripts.dev).toBe('rsbuild');
  expect(pkgJson.scripts.build).toBe(expectedBuildScript);
  expect(pkgJson.devDependencies['@rsbuild/core']).toBeTruthy();
};
```

**Flow:** remove stale dir → exec real binary with `-t` (+ repeated `--tools` flags) → assert universal manifest contract → suite-level template assertions (deps present/absent, tsconfig iff `-ts`, exact config-file snapshots) → optional cleanup via returned `clean()`.
**Invariant:** The helper pins the INVARIANTS (dev script is bare `rsbuild`; build default `'rsbuild build'`; vue/ts templates override to `'vue-tsc && rsbuild build'` via `expectedBuildScript`), while each suite pins the per-template DELTAS. Snapshot equality on config files means whitespace/quote style is contractual.
**Probe:** anchored at repo root: `grep -n "expectedBuildScript = 'rsbuild build'" e2e/cases/create-rsbuild/helper.ts` → line `10`; `sed -n '299,341p' e2e/cases/create-rsbuild/tools.test.ts | grep -c 'configContent).toBe'` → `1` (the order-independence twin pair lives exactly there).
**Probe (static):** `grep -n 'vue-tsc && rsbuild build' e2e/cases/create-rsbuild/tools.test.ts e2e/cases/create-rsbuild/tsTemplates.test.ts` → tools.test.ts `:216`, tsTemplates.test.ts `:26`,`:34`.

Direct tests ARE this capsule's subject: 22 + 58 + 63 + 347 lines across four files; notable pins: sub-dir and relative-dir creation (basic.test.ts `:14-22`), alias twins `vue3`→vue outcomes (jsTemplates.test.ts `:39-44`), solid vs solid2 discriminated by `@solidjs/web` presence (jsTemplates.test.ts `:40-52`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "createAndValidate expectPackageJson", limit: 5 });
```
Live-resolved 2026-08-24 at `2bcf61c`: rank#1 = `helper.createAndValidate` node in `e2e/cases/create-rsbuild/helper.ts` line-exact.

## Verdict
Adopt the exec-real-binary + inspect-artifacts harness shape for any scaffolder (no unit-mocking of the CLI), the universal-manifest vs per-template-delta split, CRLF normalization before snapshot compare, and exact-string config snapshots as the formatting contract. Adapt assertion helpers to your test runner. Omit nothing else — the pattern is small and complete. Caveat: requires the workspace-built bin path; porters need an equivalent build step before running these suites.
