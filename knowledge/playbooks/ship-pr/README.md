---
title: ship-pr
summary: 'Use when the user wants a change shipped autonomously end to end: commit, push, open the PR, watch CI, triage and address bot/human review comments in-thread, resolve threads, and merge when everything is green (''ship it'', ''run the full PR cycle'', ''commit, push, PR, and merge if clean''). Runs to merge without per-step asks. NOT for stepwise asks: pushing only, opening a PR only, addressing review feedback only, or merging an existing PR only (push-pr owns those).'
kind: playbook
---

# Ship PR

This is the orchestration layer for an explicitly requested full lifecycle through
merge. Individual push, PR, review, or merge requests belong to
`../push-pr/README.md`. Full-cycle authorization permits merge, but evidence still
gates it. If the repository has no quality gate, report that gap instead of
inventing CI or claiming a clean full cycle.

## Loop

1. Inspect authored scope and the requested/default base. Create a branch and
   scoped conventional commits without unrelated changes. Run the repository's
   gates on the committed tree and `git diff --check <base>...HEAD` (merge base; the
   comparison rule lives in `../git-workflow-and-versioning/README.md`). A red local
   gate blocks push.
2. Load `../push-pr/README.md` and use its evidence, template, PR creation/update,
   and metadata procedure. Do not duplicate endpoint mechanics here.
3. Watch required CI to a final state. Read review findings, not just review-bot
   status. For each feedback cycle, use
   `../push-pr/references/review-threads.md`: verify findings against source, fix
   and test valid issues, commit/push, reply in-thread, then resolve appropriately.
   Rebut invalid findings with evidence in-thread; leave them open for reviewer
   confirmation when needed. A reply alone never resolves a thread.
4. For conflicts, integrate the current base and rerun gates before pushing.
   Repeat verification after every fix; stop and report findings requiring a
   human decision.
5. Merge only with `mergeStateStatus: CLEAN`, green local gates and required CI,
   and every review thread resolved. Use a repository-allowed merge method;
   never bypass protections. Auto-merge is not implied by repository capability.
6. Delete the merged task branch and sync the local base without discarding user
   work. Before deleting, fetch and compare (`git fetch origin <branch> && git log
   --oneline <merged-head>..FETCH_HEAD`): a concurrent session can push commits whose PR
   is already merged, so they carry no PR at all, and a stale remote-tracking ref makes
   the log look empty. Land those through a fresh PR or report them explicitly. If
   local changes prevent safe cleanup, report the remaining cleanup rather than reset
   them.

Verify completion with `gh pr view <n> --json state,mergedAt,mergeCommit,statusCheckRollup`
(`MERGED`, a merge SHA, and the newest run of each check passing — superseded runs
may appear `cancelled`, see `../push-pr/references/ci-and-observation.md`) plus
paginated GraphQL `reviewThreads.isResolved` all true. Report the PR link, merge
SHA, and any cleanup limitation. Commit/merge conventions belong to
`../git-workflow-and-versioning/README.md`.
