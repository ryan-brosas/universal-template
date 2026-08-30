<!-- capsule-v2 -->
# Scope guard — the meta-tests that turn repo conventions (deps, CI, workflows) into failing assertions

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory` (full mode 380n/941e @2026-08-22T23:46:09Z). **Question:** How do you enforce supply-chain and workflow invariants — "this fork uses only OUR packages, CI stays fast, publish is pinned" — so violations break the build instead of relying on review?

## Scope guard
**Path/Symbol:** `test/unit.test.ts:"runtime package scope"` describe (:126–154), `"GitHub Actions workflows"` describe (:156–204); fixtures read: `../index.ts`, `../CLAUDE.md`, `../bun.lock`, `../package.json`, `../.github/workflows/{ci,e2e,publish-npm,windows-qmd-smoke}.yml`.
**Signature:** `test("uses the official @earendil-works Pi packages", () => { const source = fs.readFileSync(new URL("../index.ts", import.meta.url), "utf-8"); ... })`.
**Data Shape:** Pure text assertions over file bytes: source must import `@earendil-works/pi-ai` + `@earendil-works/pi-coding-agent`, never `@mariozechner/*`; package.json pins devDeps exactly (`0.84.1`), peers as ranges (`>=0.81.1`), `engines.node >=22.19.0`, and peerDependencies for the old scope AND `@sinclair/typebox` must be ABSENT.

### Decisive source
```ts
// :133-152 — the fork-boundary contract as executable assertions
expect(source).toContain('from "@earendil-works/pi-ai"');
expect(source).not.toContain("@mariozechner/pi-ai");
expect(packageJson.devDependencies["@earendil-works/pi-ai"]).toBe("0.84.1");
expect(packageJson.peerDependencies["@mariozechner/pi-ai"]).toBeUndefined();
// :171-176 — one install per OS, no matrix, no secrets in the fast path
expect(ciWorkflow.match(/- run: npm ci/g)).toHaveLength(2);
expect(ciWorkflow).not.toContain("matrix:");
expect(ciWorkflow).not.toContain("OPENAI_API_KEY");
```

**Flow:** (1) The runtime-scope test reads four files at module load and asserts imports/lockfile/package.json all agree on the new package scope — a re-introduced old dependency fails in ANY of the three surfaces. (2) The workflow tests pin per-workflow contracts: feature-branch CI with concurrency-group cancel-in-progress; exactly two `npm ci` steps across ubuntu+windows jobs; a path-filtered Windows qmd smoke pinned to `QMD_VERSION: "2.5.3"` with actions/cache@v4; e2e manual-dispatch-only (`workflow_dispatch:` present, NO `pull_request:` trigger) because it burns API keys; npm publish on `v*` tags at node 22.19.0 with `id-token: write` + `--provenance` + tag-derived version `${GITHUB_REF_NAME#v}`.

**Invariant:** convention drift is caught by the unit suite itself, not by humans reading diffs; the API-key-backed path can never silently start running on PRs.

**Probe:** same suite run as test-harness (182 pass incl. these describes); the workflow fixtures live under `.github/workflows/` on disk (graph-uncovered — read directly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "runtime package scope GitHub Actions workflows", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: encode fork/scope boundaries and CI-shape contracts as meta-tests that read raw files. Adapt the asserted values to your own dependency scopes and workflow names. Omit nothing if you maintain a fork or vendor a repo — this is how pi-memory prevents silent upstream bleed.
---
