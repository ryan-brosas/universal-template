<!-- capsule-v2 -->
# Single-binary execution transport — where is docker-vs-native actually decided, and what must a CI adapter inject around the executable?

**Source:** qodana-action Apache-2.0 `main@e0675fbe…`; Codebase Memory `qodana-action`. **Question:** Three CI adapters wrap one CLI. Who owns the docker/native decision, what env and argv does each host owe the binary, and how do exit codes travel back?

## Host runner bodies around one EXECUTABLE
**Path/Symbol:** `scan/src/utils.ts:qodana` (:208-231), `vsts/src/utils.ts:qodana` (:111-140), `gitlab/src/utils.ts:qodanaScan` (:296-319) + `qodanaExec` (:272-294); argv builder `common/qodana.ts:getQodanaScanArgs` (:236-255); pull gating `prepareAgent` (scan :344-361, vsts :183-199; gitlab has NO pull phase — its `getInputs` forces native unless QODANA_DOCKER, see env-input-surface).
**Signature:** scan/vsts `qodana(inputs, args=[]): Promise<number>`; gitlab `qodanaScan(): Promise<number>` via `qodanaExec(args)`.
**Data Shape:** argv = `['scan','--cache-dir',cacheDir,'--results-dir',resultsDir] + ('--skip-pull' if !isNativeMode) + userArgs + ['--commit',sha? in PR mode]`.

### Decisive source
```ts
// common/qodana.ts — the whole transport "mode" signal:
if (!isNativeMode(args)) { cliArgs.push('--skip-pull') }
cliArgs.push(...args)
// scan/src/utils.ts qodana():
const exit = await exec.getExecOutput(EXECUTABLE, args, {
  ignoreReturnCode: true,
  env: { ...process.env, QODANA_REVISION: getHeadSha(), NONINTERACTIVE: '1' }
})
return exit.exitCode
// gitlab/src/utils.ts qodanaExec(): raw spawn, never rejects
const proc = spawn(EXECUTABLE, args, {stdio: 'inherit'})
proc.on('close', (code, signal) => code == null ? resolve(1-with-signal-log) : resolve(code))
proc.on('error', err => resolve(127))   // binary missing → 127, not a throw
```

**Flow:** adapters NEVER compose docker commands — the CLI reads `--ide` / `--within-docker[=]false` and decides natively; docker-mode runs are pre-warmed by a separate whitelisted `qodana pull` (see pull-args-filtering) and then told `--skip-pull` so the image is reused, native-mode omits it. PR mode appends `--commit <merge-base-or-sha>` behind per-host gates (scan: payload.pull_request exists; vsts: `Build.Reason === 'PullRequest'`; gitlab: `isMergeRequest()`); branch identity travels as env — scan always sets `QODANA_REVISION`, vsts/gitlab set `QODANA_BRANCH` only in PR builds (vsts strips `refs/heads/` from `System.PullRequest.SourceBranch`, gitlab copies `CI_MERGE_REQUEST_SOURCE_BRANCH_NAME`). All three pass `NONINTERACTIVE=1` and `ignoreReturnCode`/never-reject so the numeric exit code flows back untouched for the exit-code algebra (orchestrator-phase-structure). A failed pull is RECORDED but never aborts the scan phase: scan's prepareAgent returns after `core.setFailed('qodana pull failed…')` and main still runs `qodana()`.
**Invariant:** The host owns provisioning, env injection, and exit-code plumbing ONLY — mode semantics belong to the binary. Corollary: any new host must replicate the exact argv prefix order (`scan --cache-dir --results-dir [--skip-pull]`) because the pull/scan pair coordinates image reuse through `--skip-pull`, not through host state.
**Probe:** EXECUTED at pin: `cd scan && ../node_modules/.bin/jest --config jest.config.js __tests__/main.test.ts` → **11 passed**, incl. `'qodana scan command args'` (:85-93) pinning `getQodanaScanArgs` against `defaultDockerRunCommandFixture()`; common suite → **62 passed** (pull-args table). gitlab/vsts runner bodies have no upstream tests — pinned by ranges (coverage caveat).
**Coverage caveat:** none — all cited paths `no_recorded_issue`, generation_matches=true.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "qodanaScan qodanaExec NONINTERACTIVE spawn executable", limit: 6 });
```
(rank-1 `gitlab.src.utils.qodanaExec` :272-294 at execution time; the vsts/QodanaScan/index.js rows are webpack BUILD OUTPUT — never cite.)

## Verdict
Adopt "one binary decides its own execution mode; hosts inject env+argv and plumb exit codes" for any tool wrapper spanning containerized and bare-metal runners; adapt the per-host PR gate and branch-env names to your platform's payload; omit the signal/127 spawn fallbacks only if your host rejects instead.
