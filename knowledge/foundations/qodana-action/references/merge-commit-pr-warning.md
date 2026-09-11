<!-- capsule-v2 -->
# Merge-commit checkout guard — how do you detect (and only warn about) a pre-merged PR checkout before diff-scoped analysis?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** When a CI system checks out a merge commit instead of the PR head, diff-scoped analysis silently scans wrong files — how does the action detect that situation and what does it do?

## Parent-count detection, warning-only enforcement
**Path/Symbol:** `common/utils.ts:isMergeCommit` (:44-46), `MERGE_COMMIT_PARENTS_ARGS` (:34-39), `MERGE_COMMIT_PR_WARNING` (:28-31); consumers `scan/src/utils.ts:warnIfMergeCommitCheckout` (:184-194), `gitlab/src/utils.ts:warnIfMergeCommitCheckout` (:321-336), `vsts/src/utils.ts:warnIfMergeCommitCheckout` (:257-273).
**Signature:** `isMergeCommit(parents: string): boolean` over `git show --no-patch --format=%P HEAD`.
**Data Shape:** Input = stdout of `%P` (space-separated parent hashes; empty for root commits). Output = boolean; side effect = one platform warning, never a failure.

### Decisive source
```ts
export function isMergeCommit(parents: string): boolean {
  return parents.trim().split(/\s+/).filter(Boolean).length >= 2
}
```
Each adapter appends its own remediation hint after the shared warning:
- GitHub: `` 'Set `ref: ${{ github.event.pull_request.head.sha }}` and `fetch-depth: 0` in your checkout step.' ``
- GitLab: `'Use a standard merge request pipeline (merged-results pipelines check out a pre-merged commit), …'`
- Azure: `'Add a "git checkout $(System.PullRequest.SourceCommitId)" step (with "fetchDepth: 0") before the scan.'`

**Flow:** before pushing `--commit <sha>` in pr-mode, each adapter runs the parents command with `ignoreReturnCode` (git may be absent/shallow) → `isMergeCommit` counts non-empty whitespace-split tokens ≥2 → warn with shared text + platform hint → continue scanning anyway. GitLab wraps its check in try/catch and drops to debug-level on failure; GitHub/VSTS tolerate nonzero exit codes silently.
**Invariant:** Detection is ADVISORY ONLY — the action never fails or disables PR mode because of a merge commit; it warns so users can fix their checkout. The git invocation must always be failure-tolerant (`ignoreReturnCode: true`); a missing git binary must degrade to "no warning", not crash the action.
**Probe:** `common/__tests__/main.test.ts` `describe('isMergeCommit')` :215-248 — single parent false, two parents true, octopus (p1 p2 p3) true, root commit '' false, whitespace-only false, tolerates surrounding whitespace/newlines true, plus a test pinning the exact `MERGE_COMMIT_PARENTS_ARGS` array.
**Coverage caveat:** adapter-level warnIf* functions are not directly tested upstream (no runner here either); behavior pinned at the pure function + constant.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "isMergeCommit MERGE_COMMIT merge checkout warning", limit: 6 });
```

## Verdict
Adopt the `%P`-parent-count detector and the shared-warning + platform-hint split (one canonical message text, three remediation strings keyed to each host's checkout model); adapt the warning emitters; omit any temptation to hard-fail — the deliberate softness IS the contract.
