<!-- capsule-v2 -->
# CI double-run choreography — validate strictly once, then re-run harmlessly for a summary

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does CI run the same validation script twice — once as the real failing gate and once only to capture a human-readable step summary — without the summary run masking or flaking the build result?

## Validate-fail-fast then tail-for-summary
**Path/Symbol:** `.github/workflows/check.yml` (whole file, 27 lines); job `check` steps `Validate template surface` (id `check`, :19–21) and `Collate results` (:22–26).
**Signature:** step 1 `run: node scripts/check.mjs` (exit code IS the job result); step 2 `if: always()` + `run: node scripts/check.mjs 2>&1 | tail -1 >> "$GITHUB_STEP_SUMMARY"; exit 0`.
**Data Shape:** triggers `push→main` + all `pull_request`s; `concurrency.group: check-${{ github.ref }}` with `cancel-in-progress: true` collapses superseded runs on the same ref; runner `ubuntu-latest`, `actions/checkout@v7`, `actions/setup-node@v7` with node 24.

### Decisive source
```yaml
steps:
  - uses: actions/checkout@v7
  - uses: actions/setup-node@v7
    with:
      node-version: 24
  - name: Validate template surface
    id: check
    run: node scripts/check.mjs            # real gate: nonzero exit fails the job
  - name: Collate results
    if: always()                           # even after failure, produce the summary
    run: |
      echo '## Check results' >> "$GITHUB_STEP_SUMMARY"
      node scripts/check.mjs 2>&1 | tail -1 >> "$GITHUB_STEP_SUMMARY"
      exit 0                               # summary run can NEVER flip the verdict
```

**Flow:** (1) checkout + node 24; (2) first execution is the authority — any validator failure exits 1 and fails the job; (3) second execution is guarded `if: always()` so it also runs when step 1 failed, appending only the final status line (`repository check: ok` / `dsh-template check: FAILED (N problems)`) to `$GITHUB_STEP_SUMMARY`; (4) `exit 0` hard-codes the second run as side-effect-free with respect to the verdict.
**Invariant:** exactly ONE run owns the pass/fail signal; the other is presentation-only (`tail -1` + `exit 0`); because the script is deterministic and read-only over the work tree, running it twice is safe — this only holds for idempotent validators (it would be wrong for a script with side effects). Local/CI parity is exact: the same `node scripts/check.mjs` line is the documented local gate (AGENTS.md golden rule).
**Probe:** `.github/workflows/check.yml:19–26` (this file; indexed `no_recorded_issue` + `metadata_match`). Behavioral half: `node scripts/check.mjs` executed at HEAD → exit 0, last line `repository check: ok` — the exact string the summary step would capture. Coverage caveat: workflow semantics are GitHub-hosted; not executable here beyond the local half.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "check failures section skillFiles packs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split (strict gate run + `always()` summary run ending in `exit 0`) and the single-line `tail -1` summary contract for any deterministic validator; adopt ref-scoped `cancel-in-progress` concurrency for PR pipelines. Adapt trigger branches, node version, and summary format to the host. Omit for non-idempotent checks (anything writing state must not run twice).
