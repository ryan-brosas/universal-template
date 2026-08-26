<!-- capsule-v2 -->
# Upstream CI gates — which suites does microsoft/TypeChat actually enforce, and how do you replicate the gate?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** Before trusting or extending a port, which test planes does upstream CI actually run — and which "tests" are local-only?

## Python matrix vs JS build-only
**Path/Symbol:** `.github/workflows/ci.python.yml:17-71` (jobs: pyright + pytest); `.github/workflows/ci.js.yml:23-41` (single job: build).
**Signature:** python job = 3.11/3.12/3.13/3.14 × ubuntu, `fail-fast: false`; js job = node 22.x/24.x/26.x.

### Decisive source
```yaml
# ci.python.yml — version is read from the package's own manifest:
PYRIGHT_VERSION=$(jq -r '.devDependencies.pyright' < package.json)
...
- name: Test with Pytest
  run: |
    pytest -vv
```
```yaml
# ci.js.yml — the ENTIRE step list for the TypeScript side:
- run: npm ci
- run: npm run build-all
```
**Flow:** python: hatch env create → pyright (pinned by `python/package.json` devDependencies, one job annotated) → `pytest -vv` per interpreter. js: clean install + build across three node majors. That's all.
**Invariant:** THE TYPESCRIPT TEST SUITES ARE NOT CI-ENFORCED — `typescript/test/{program,validate,zod}.test.ts` and `tests/model.test.mjs` never execute in CI; a TS regression ships if it still builds. The Python snapshot fleet IS enforced on four interpreters (which is why per-version snapshot dirs exist and why adjudicating a "stale" snapshot requires running the matching interpreter). Environment provisioning contract: python deps flow through hatch (`hatch env create`), with `virtualenv<20.29` pinned in the workflow — a porter reproducing the gate should mirror that pin rather than bare pip. This asymmetry also explains evidence practice in this leaf: Python claims carry live-suite pins, TS claims rest on direct reads plus locally-run suites.
**Probe:** executed static pins: ci.js.yml contains exactly one `run:` application step — `grep 'run: npm run|pytest' .github/workflows/ci.js.yml`=1 @41 (`build-all`), pytest=0 in that file; ci.python.yml carries the pytest step (@68-70) and the jq pyright-version extraction (@56). Repo-owned runner status this pass: pass-1 venv gone → suite not re-executed here; prior-pass execution (22 passed / 17 snapshots at this exact commit) recorded in snapshot-harness.md.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"pyright hatch pytest workflow","limit":5}'
// Workflows are File nodes without symbols — use query_graph MATCH (f:File) for inventory; content via direct read.
```

## Verdict
Adopt the two-tier trust model when consuming this leaf: Python capsules inherit CI-enforced confidence at pin; TS capsules do NOT (their probes ran locally only). Adapt by wiring the TS suites into your own pipeline before relying on them as regression guards; omit the hatch/virtualenv pinning only if your resolver already reproduces the env deterministically.
