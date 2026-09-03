---
name: ship-pr
description: "Use when the user wants a change shipped autonomously end to end: commit, push, open the PR, watch CI, triage and address bot/human review comments in-thread, resolve threads, and merge when everything is green ('ship it', 'run the full PR cycle', 'commit, push, PR, and merge if clean'). Runs to merge without per-step asks. NOT for stepwise asks: pushing only, opening a PR only, addressing review feedback only, or merging an existing PR only (push-pr owns those)."
---

# Ship PR (autonomous loop)

## Core Principle
One evidence path from working tree to merge: gates before push, a PR body built from real output, review findings triaged against the code, and a merge only after every hard signal is green. Invoking this loop pre-authorizes the merge; the evidence still gates it.

## When to Use / NOT
- **Use when:** the user asks for the full cycle in one request ("ship it", "commit, push, PR, and merge if it's clean", "handle the whole PR lifecycle").
- **NOT when:** a single step is asked for (push only, PR only, feedback only, merge only); `push-pr` owns those; or the target repo has no quality gate (report the verification gap, do not invent CI).

## Workflow
1. **Scope and branch.** Inspect the diff; split scoped conventional commits (data, behavior, tests, docs are separate concerns). Branch off `main`. Never commit unrelated churn.
2. **Gates before push.** Run the repo's verification on the committed tree (record commands + exit codes) and `git diff --check <base>..HEAD`. A red gate blocks the push.
3. **PR.** Discover the repo's PR template and fill it from real evidence (commands, exit codes, probe output). Write the body through `mktemp`, never shell-interpolated. `gh pr create --base <base>`; if a PR exists for the branch, update it instead.
4. **Watch CI.** `gh pr checks <n> --watch` to a final state. A green review-bot check is not "no findings"; fetch the threads.
5. **Review triage.** REST `pulls/<n>/comments` + GraphQL `reviewThreads` every cycle. For each finding: verify against the code first. Valid → smallest fix, extend probes where the repo demands them, gates, commit, push → reply **in-thread** `Updated in <sha>.` + what changed → resolve the thread. Invalid → rebut **in-thread** with evidence and leave it unresolved for the reviewer. Conflicts → merge/rebase `main`, re-run gates, push.
6. **Merge when all hold:** `mergeStateStatus` `CLEAN`, required checks green, every thread resolved (a rebuttal backed by evidence is a deliberate disposition; findings needing a human decision do not count, so stop and report instead), local gates green. Use a merge method the repo allows (`gh repo view --json *MergeAllowed`), delete the branch, sync `main`.
7. **Stop:** report the PR link, merge sha, and any threads left for a human.

## Red Flags
- **HARD-GATE:** never merge with failing required checks or unresolved threads.
- **HARD-GATE:** a green review-bot check is not "the review has no findings"; fetch and read the threads.
- **HARD-GATE:** never resolve a thread merely because a reply was posted; never merge while a thread waits on a human decision.
- **HARD-GATE:** never push with a red gate; never fabricate evidence, SHAs, CI states, or probe output.
- **HARD-GATE:** replies go in-thread (REST `in_reply_to` = the top-level comment's database id; thread state lives on the GraphQL `PRRT_…` node id, a different id).
- Do not hand-add labels/milestones automation derives; do not enable auto-merge unless the user asked.

## Verification
- `gh pr view <n> --json state,mergedAt,mergeCommit` → `MERGED` with a sha; `gh pr checks <n>` all pass; `gh api .../reviewThreads` → all `isResolved`; local gates exit 0 on the final tree; `main` synced, branch deleted.

## Related
- `push-pr` skill: the full in-thread reply/resolution protocol (REST + GraphQL id semantics, body construction, template discovery).
- `git-workflow-and-versioning` skill: commit/merge-method conventions.
