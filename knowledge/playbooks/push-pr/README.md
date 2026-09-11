---
title: push-pr
summary: Use when finished work needs to be pushed and opened or updated as a GitHub pull request, when PR review feedback must be addressed in its thread, or when an open PR should be auto-merged on request. Runs the project's own gates and builds the PR body from real evidence.
kind: playbook
---

# Push PR

Use one evidence path: local checks verify the branch, CI verifies the pushed
commit, and the PR body records scope, proof, and limitations. This skill owns
individual PR and review operations; `../ship-pr/README.md` owns a requested full
lifecycle through merge. An existing PR is updated, not duplicated.

## Workflow

1. Inspect status, the base branch, commit range, and authored diff. Run the
   project's relevant gates and `git diff --check` on that range; record commands
   and exit statuses. Pre-PR, also run `coderabbit review --agent` (add `--light`
   for large diffs; `--committed` when the tree is clean) and triage the
   structured findings before opening: fix valid correctness findings, skip the
   rest with a one-line reason, and note skipped conflicts with prior reviewed
   behavior. If no quality gate exists, run the strongest applicable
   checks and report the gap rather than inventing CI. Use
   `../pre-pr-validation/README.md` for local readiness and revision-bound evidence.
   A blocked local verdict stops delivery unless the user requests a draft/WIP PR;
   carry the blockers honestly into that draft.
2. For PR creation or body updates, load `references/pull-request-format.md`.
   Use the repository's own template first; fall back to
   `../../../templates/pull-request.md`. Include only evidence actually obtained.
   Visual changes need rendered proof; structural observations and prior-art
   provenance follow the change. Mark a reusable lesson as a capture candidate,
   not an automatic capture task.
3. Write Markdown to a securely created temporary file (`mktemp`); pass it with
   `--body-file`, never interpolate it into shell code. Before `gh pr create`, run
   the `../gh-repo-target-guard/README.md` check: gh's default repo
   (`gh repo set-default --view`) must match the intended base from `git remote -v`;
   in any fork checkout pass `--repo` (and `--head` when head and base repos
   differ) explicitly. Push and create with
   `gh pr create --title "..." --body-file <file> --base <base>`, or update the
   existing PR. Incomplete implementation is draft; ready implementation can
   enter review while CI runs. A failing required check blocks merge, not review.
4. Apply labels only when explicitly requested; this repository has no label
automation. Reviewers follow CODEOWNERS or an
   explicit request; milestones/projects follow issue relationships. Link only
   real issues. If the batch already landed on the base branch, move it to a
   feature branch first — `git reset --soft` to the pre-batch point keeps the
   working tree identical so live watchers do not restart — push the branch,
   then restore the base with `--force-with-lease` before opening the PR.
   Auto-merge requires an explicit user request, not merely repository
   support, and must not be enabled while required checks fail.
5. Watch required CI to a terminal state with `gh pr checks --watch` (or
   `gh run watch`); do not rely on a single unwatched poll.
   Update the PR evidence when results change. For workflow or conditional
   observation details, select `references/ci-and-observation.md`; CI authoring
   belongs to `../github-actions-engineering/README.md`.
6. For review feedback, load `references/review-threads.md` **before replying or
   resolving**. Read the findings, verify against source, fix and test where
   warranted, reply in-thread, and resolve only addressed or deliberately
   dispositioned findings. Anything needing reviewer confirmation stays open.

## Boundaries and stop condition

A review-only request authorizes reading, fixes, in-thread replies, and justified
resolution, not unrelated GitHub writes. Replying is not resolution. REST comment
database IDs and GraphQL review-thread IDs are different; the reference owns
endpoint and payload mechanics.

Never merge with a failing local gate, failing required check, unresolved thread,
or pending human decision. A green review-bot check does not mean no findings:
fetch and read the threads before merging. Do not invent evidence or SHAs, include
secrets/unrelated files, or use `pull_request_target` for untrusted branch code.

Stop at the requested operation: the PR exists or is updated, evidence matches
observed checks, and review feedback is handled or explicitly blocked. Report
remaining gaps; do not expand an individual operation into an unrequested merge.
