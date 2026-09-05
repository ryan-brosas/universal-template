---
name: push-pr
description: "Use when finished work needs to be pushed and opened or updated as a GitHub pull request, when PR review feedback must be addressed in its thread, or when an open PR should be auto-merged on request. Runs the project's own gates and builds the PR body from real evidence."
invocation: entry
---

# Push PR

Use one evidence path: local checks verify the branch, CI verifies the pushed
commit, and the PR body records scope, proof, and limitations. This skill owns
individual PR and review operations; `../ship-pr/SKILL.md` owns a requested full
lifecycle through merge. An existing PR is updated, not duplicated.

## Workflow

1. Inspect status, the base branch, commit range, and authored diff. Run the
   project's relevant gates and `git diff --check` on that range; record commands
   and exit statuses. If no quality gate exists, run the strongest applicable
   checks and report the gap rather than inventing CI.
2. For PR creation or body updates, load `references/pull-request-format.md`.
   Use the repository's own template first; fall back to
   `../../templates/pull-request.md`. Include only evidence actually obtained.
   Visual changes need rendered proof; structural observations and prior-art
   provenance follow the change. Mark a reusable lesson as a capture candidate,
   not an automatic capture task.
3. Write Markdown to a securely created temporary file (`mktemp`); pass it with
   `--body-file`, never interpolate it into shell code. Push and create with
   `gh pr create --title "..." --body-file <file> --base <base>`, or update the
   existing PR. Incomplete implementation is draft; ready implementation can
   enter review while CI runs. A failing required check blocks merge, not review.
4. Let repository automation derive labels. Reviewers follow CODEOWNERS or an
   explicit request; milestones/projects follow issue relationships. Link only
   real issues. Auto-merge requires an explicit user request, not merely repository
   support, and must not be enabled while required checks fail.
5. Watch required CI to a terminal state with `gh pr checks --watch` (or
   `gh run watch`); do not rely on a single unwatched poll.
   Update the PR evidence when results change. For workflow or conditional
   observation details, select `references/ci-and-observation.md`; CI authoring
   belongs to `../github-actions-engineering/SKILL.md`.
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
