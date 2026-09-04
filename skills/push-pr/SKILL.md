---
name: push-pr
description: "Use when finished work needs to be pushed and opened or updated as a GitHub pull request, when PR review feedback must be addressed in its thread, or when an open PR should be auto-merged on request. Runs the project's own gates and builds the PR body from real evidence."
invocation: entry
---

# Push PR

## Core Principle

Use one evidence path for every pull request. The local gate checks the branch. GitHub Actions checks the pushed commit. The PR body stores the scope, proof, and CI result; conditional evidence (visual, structural) follows the change, and a reusable lesson is only marked as a `leverage-capture` candidate.

## When to Use / NOT

- **Use when:** a verified branch needs a pull request.
- **Use when:** the project defines a quality workflow that guards its branches (`github-actions-engineering` authors or reviews it; the standard shape is `../../templates/github-pr-ci.yml`).
- **Use when:** a review must show screenshots, CI state, or graph evidence.
- **NOT when:** the project defines no quality gate. Run the strongest applicable checks (build, tests, lint, `git diff --check`), report the verification gap in the PR body, and do not invent CI that does not exist.
- **NOT when:** an open PR already covers the branch. Update that PR.

## Workflow

1. Inspect the branch and diff: `git status`, `git log <base>..HEAD`, `git diff <base>...HEAD`. Record the base branch and what changed.
2. Run the relevant project verification (the project's gates for the touched surface, not every gate in existence). Save each command and its exit status. Run `git diff --check` on the branch range.
3. Discover the repository's own PR template first, `.github/PULL_REQUEST_TEMPLATE.md`, `PULL_REQUEST_TEMPLATE/` directory, `docs/`, or the repository root (GitHub-supported locations; re-verify when GitHub changes them). Use the repository's template when one exists; fall back to `../../templates/pull-request.md` otherwise.
4. Construct the PR body from actual evidence, scope, what changed and why, verification output, run links. Never fabricate completed checks; mark absent values `None`. Conditional sections only when they apply: **visual change** → actual before/after screenshot or rendered evidence; **complex structural change** → Fovea/Steroid observation when useful; **external/reference implementation** → provenance + license note; **reusable lesson** → mark as a `leverage-capture` candidate (do not capture automatically).
5. Write the body to a securely created temporary file (`mktemp`), never interpolate generated Markdown into the shell command.
6. Push and create the PR: `gh pr create --title "..." --body-file <file> --base <base>`. **Draft policy:** implementation incomplete → `--draft`; implementation ready → open ready for review and let CI run in parallel (review and CI are parallel activities). A failing required check blocks the merge, not the review.
7. **Metadata after creation:** let deterministic repository automation label the PR (area labels from changed paths; type and breaking-change labels from the title) and do not hand-add labels automation derives. Link issues deliberately in the body: `Closes #N` only when the PR fully fixes the issue, `Refs #N` when informational, never a guessed closure. Reviewers come from CODEOWNERS or an explicit request; milestones and projects inherit from issue relationships only. Enable auto-merge only on an explicit user request (`gh pr merge --auto`) - the repository capability is not per-PR permission.
8. Watch the required CI to a final state (`gh pr checks` / `gh run watch`); update the body when state changes; confirm the result before claiming done.
9. Address review feedback when requested, the in-thread procedure below.

Stop when the PR exists, the body reflects actual evidence, required CI is green or the failure is owned, and review feedback (if any) is handled per the in-thread contract.

## Review feedback (in-thread)

"Address the PR review comments" authorizes exactly the review workflow, read the threads, implement fixes, reply in-thread, resolve addressed threads, and no other GitHub writes (no unrelated comments, deletions, metadata changes).

1. **Enumerate threads.** REST: `gh api repos/OWNER/REPO/pulls/NUMBER/comments` (review comments). GraphQL: `repository.pullRequest.reviewThreads` for thread state.
2. **Distinguish ids.** A top-level review comment has `in_reply_to_id: null`; its **database id** is what replies anchor to. Thread state lives on the GraphQL **review-thread node id** (`PRRT_…`), a different identifier from the REST comment id. Never conflate them.
3. **Implement and verify** the feedback locally (project gates) before replying.
4. **Reply in-thread**, never as a new top-level comment: `POST /repos/OWNER/REPO/pulls/NUMBER/comments` with `in_reply_to` = the top-level comment's database id. Pass the body through a file/stdin, `gh api --input <file>` with the payload JSON (put GraphQL query AND variables inside the JSON body; `-f`/`-F` fields do not bind GraphQL variables when `--input` is used, verified live 2026-08-30).
5. **Resolve** with GraphQL `mutation { resolveReviewThread(input: {threadId: "PRRT_…"}) { thread { isResolved } } }`, only when the feedback is addressed or deliberately dispositioned AND the requested workflow authorizes resolution. Feedback needing reviewer confirmation stays unresolved; posting a reply is never resolution.
6. **Reply format:** `Updated in <sha>.` + what changed + verification when relevant. No invented SHAs; no social filler ("great catch", "thanks").

Verified live on this repository (PR #10, 2026-08-30): REST list returned `{id, in_reply_to_id: null, pull_request_review_id}`; GraphQL reviewThreads returned `PRRT_…` node ids whose `comments.nodes[].databaseId` map to the REST ids. Re-verify endpoint shapes before relying on them, do not freeze these recipes.

## Red Flags

- **HARD-GATE:** a failing local gate or failing required check blocks the MERGE. A ready PR with CI still running is normal; review and CI run in parallel.
- Do not invent screenshots, tests, CI states, PR links, labels, milestones, assignees, or reviewers, absent evidence is marked `None`, never faked.
- Do not run every observation surface for every PR, evidence follows the change (visual → rendered proof; structural → graph when useful).
- Do not add secrets, `.env` files, or unrelated files.
- Merging, or enabling auto-merge on, a PR whose required checks are failing. HARD-GATE.
- Enabling auto-merge without an explicit user request. HARD-GATE.
- Hand-adding type/area/breaking-change labels that repository automation derives from the title and changed paths.
- Do not use `pull_request_target` for untrusted branch code.
- Resolving a review thread merely because a reply was posted. HARD-GATE.
- Merging while review threads are unresolved, or treating a green review-bot check as "the review has no findings" - fetch and read the review threads before merging. HARD-GATE.
- Replying to review feedback as a new top-level comment instead of in-thread.
- Confusing the REST review-comment id with the GraphQL thread node id. HARD-GATE.

## Verification

The PR exists with a body whose claims trace to real evidence (diff, commands + exit codes, run links). required checks are green or the failure is owned with a plan. metadata matches the project or is absent by policy. review feedback handled per the in-thread contract. No invented evidence anywhere in the body.

## References

- `references/pull-request-format.md` - fixed PR body order and evidence fields.
- `references/ci-and-observation.md` - workflow events, anti-slop checks, graph observation, and learning.
- `../github-actions-engineering/SKILL.md` - the skill that authors and reviews the workflow file.
