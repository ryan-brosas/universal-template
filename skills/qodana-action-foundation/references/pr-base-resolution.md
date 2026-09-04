<!-- capsule-v2 -->
# PR-base resolution ladder — how do you compute the right merge-base for diff-scoped analysis when CI metadata lies?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** Which commit should `--commit` receive in PR mode, in what precedence, and what happens when every source fails?

## env override → fresh merge-base → webhook SHAs → disable PR mode
**Path/Symbol:** GitHub `scan/src/utils.ts:getPrSha` (:132-182), `getHeadSha` (:196-206); GitLab `gitlab/src/utils.ts:getPrSha` (:338-367); Azure `vsts/src/utils.ts:getPrSha` (:275-308) + `getSourceAndTargetBranches` (:244-255); trigger points scan `qodana()` (:208-231), gitlab `qodanaScan()` (:296-319), vsts `qodana()` (:111-140).
**Signature:** `getPrSha(): Promise<string>` — empty string means "run without PR mode".
**Data Shape:** Consumes PR payload (number/head.sha/base.ref/base.sha) or platform vars (`CI_MERGE_REQUEST_*`, `System.PullRequest.*`), plus env overrides `QODANA_PR_SHA` / `QODANA_REVISION`.

### Decisive source
```ts
// Step 1: Fetch up-to-date branches and compute merge-base
// This avoids the stale pr.base.sha issue:
// https://github.com/orgs/community/discussions/59677
const fetchResult = await gitOutput(['fetch', 'origin', targetBranch, sourceBranch], {ignoreReturnCode: true})
if (fetchResult.exitCode === 0) {
  const mergeBase = await gitOutput(['merge-base', `origin/${targetBranch}`, `origin/${sourceBranch}`], {ignoreReturnCode: true})
  if (mergeBase.exitCode === 0) return mergeBase.stdout.trim()
}
// Step 2: Fall back to webhook payload SHAs
core.warning('Unable to compute merge-base using git. Please specify fetch-depth: 0 …')
const webhookMergeBase = await gitOutput(['merge-base', pr.base.sha, pr.head.sha], {ignoreReturnCode: true})
...
// Step 3: Nothing worked — disable PR mode
core.warning('Unable to determine the base commit for PR analysis. The analysis will run without PR mode.')
return ''
```

**Flow:** `QODANA_PR_SHA` env wins outright → try fresh `fetch origin <target> <source>` + `merge-base origin/target origin/source` (GitHub needs `fetch-depth: 0`; the webhook base.sha is documented-stale per community discussion #59677) → fall back to merging the PAYLOAD shas locally → give up with '' and let the scan run full-scope. Independently, `getHeadSha()` (scan) resolves the REVISION passed as `QODANA_REVISION` env into the child process: env override → pr.head.sha → push sha; GitLab/VSTS instead export/propagate `QODANA_BRANCH` from their MR/source variables so the CLI reports the right branch.
**Invariant:** Every git call in the ladder is failure-tolerant until the FINAL fallback, which must return EMPTY STRING — never throw — so a metadata-less runner degrades to full analysis rather than failing the build. The '--commit' argument is only appended when sha !== ''.
**Probe:** no direct unit tests for getPrSha (coverage caveat recorded); graph probe: search_graph "merge-base pull request sha" returns all four implementations line-exact (getPrSha scan:132-182 / gitlab:338-367 / vsts src:275-308 + bundle twin); behavior pinned by range reads.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "getPrSha merge-base QODANA_PR_SHA", limit: 6 });
```

## Verdict
Adopt the four-step ladder and its never-throw terminal state for any diff-scoped tool on CI; adapt branch-variable names per host; keep the stale-webhook-sha citation — it's WHY step 1 exists and the most commonly re-made mistake.
