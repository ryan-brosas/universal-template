<!-- capsule-v2 -->
# Quick-fixes push pipeline — how do you commit machine-authored changes back to a PR safely from a read-mostly CI checkout?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** What is the exact git choreography for `push-fixes: branch|pull-request`, and which steps are allowed to fail silently?

## add→commit(gate)→rebase→branch/cherry-pick→push(+PR), bot identity everywhere
**Path/Symbol:** `scan/src/utils.ts:pushQuickFixes` (:233-300) + `createPr` via gh CLI (:787-818); `gitlab/src/utils.ts:pushQuickFixes` (:533-592) + `gitPush` URL-credential variant (:594-620) + API createPr (:622-641); `vsts/src/utils.ts:pushQuickFixes` (:516-580) + `gitPush` (:582-591) + refs/heads-prefixed createPr (:593-622).
**Signature:** `pushQuickFixes(mode: PushFixesType, commitMessage: string): Promise<void>` with `mode ∈ {none, branch, pull-request}`.
**Data Shape:** Operates on the job's checkout; identity constants `COMMIT_USER='qodana-bot'`, `COMMIT_EMAIL='qodana-support@jetbrains.com'` (common/output.ts :28-29).

### Decisive source
```ts
currentBranch = validateBranchName(currentBranch)
await git(['config', 'user.name', COMMIT_USER])
await git(['config', 'user.email', COMMIT_EMAIL])
await git(['add', '.'])
let exitCode = await git(['commit', '-m', commitMessage], {ignoreReturnCode: true})
if (exitCode !== 0) return                    // empty-diff guard: nothing to fix ⇒ done
...
exitCode = await git(['pull', '--rebase', 'origin', currentBranch])   // THROWS on failure
if (exitCode !== 0) return
if (mode === BRANCH) {
  const commitToCherryPick = (await exec.getExecOutput('git', ['rev-parse', 'HEAD'])).stdout.trim()
  await git(['checkout', currentBranch])
  await git(['cherry-pick', commitToCherryPick])
  ...
}
```
GitLab's push embeds credentials and CI suppression:
```ts
const url = new URL(`${serverUrl}/${projectPath}.git`)
url.username = COMMIT_USER
url.password = token                       // QODANA_GITLAB_TOKEN
pushArgs.push('-o', 'ci.skip', pushUrl, branch)   // prevents recursion loops
```
and appends `\n\n[skip-ci]` to the commit message (scan relies on the message the user configured; vsts default carries `[skip ci]`).

**Flow:** none→return; resolve current branch per context (PR head ref / MR source branch / push branch, refs/heads stripped on Azure) → validate charset → set bot identity → `add .` → commit with ignoreReturnCode (nonzero = clean tree = done) → log porcelain status if dirty → `pull --rebase` (hard gate; failure aborts everything) → mode BRANCH: capture HEAD sha, checkout target, cherry-pick, push → mode PULL_REQUEST: cut `qodana/quick-fixes-<sha7>`, push, open PR (gh CLI on GitHub w/ GH_TOKEN env + temp body file; gitbeaker API on GitLab; azure-devops-node-api on Azure, which requires refs/heads/ prefixes on both refs). Whole body wrapped in catch→platform-warning: quick-fixes must NEVER fail the build.
**Invariant:** The commit-step nonzero exit is SUCCESS-meaning ("nothing to fix") while rebase failure ABORTS — confusing these two inverts the semantics. Branch names must pass `validateBranchName` (`/^[a-zA-Z0-9/\-_.]+$/`) before reaching git/shell. Every push path must carry loop-suppression (ci.skip option or [skip ci]) or the bot PR triggers itself.
**Probe:** no direct tests upstream for pushQuickFixes (coverage caveat); deterministic probes: search_graph resolves all four twins incl. bundle copy (pushQuickFixes scan:233-300 / gitlab:533-592 / vsts:516-580); validateBranchName pinned by `scan/__tests__/main.test.ts` :71-83.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "pushQuickFixes cherry-pick rebase quick-fixes", limit: 6 });
```

## Verdict
Adopt the choreography verbatim including its two-tier failure policy and loop-suppression duty; adapt credential injection (URL userinfo vs extraheader vs gh env); omit the gh-CLI PR creation if your host has a first-class API.
