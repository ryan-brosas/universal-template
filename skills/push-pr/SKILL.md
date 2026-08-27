---
name: push-pr
description: "Use when a verified branch needs a repeatable GitHub pull request with local quality gates, CI evidence, screenshots, Codebase Memory observation, GitHub metadata (labels, milestone, assignees, reviewers, project, draft), and a learn handoff. The github-ci-workflow skill authors the workflow file."
disable-model-invocation: true
---

# Push PR

## Core Principle

Use one evidence path for every pull request. The local gate checks the branch. GitHub Actions checks the pushed commit. The PR body stores the scope, proof, CI result, graph observation, and follow-up lesson.

## When to Use / NOT

- **Use when:** a verified branch needs a pull request.
- **Use when:** the project has `.github/workflows/pr-quality.yml` or needs the standard from `~/.agents/templates/github-pr-ci.yml` (the `github-ci-workflow` skill authors or reviews that file).
- **Use when:** a review must show screenshots, CI state, or graph evidence.
- **NOT when:** the project has no stated quality gate. Stop and ask for one.
- **NOT when:** an open PR already covers the branch. Update that PR.

## Workflow

1. Read the project `AGENTS.md`. Record the base branch, the branch name, the canonical gate, and the workflow file. When the workflow file is missing or out of date, run `github-ci-workflow` first and come back after it passes.
2. Inspect the diff and commit list. Run `agent-code-quality-gate` against scope, duplication, behavior tests, evidence, and regressions.
3. Run the project gate from the repository root. Save each command and its exit status. Run `git diff --check` on the branch range.
4. Observe the change with Codebase Memory. Probe index status and coverage for every touched path. Search or trace the touched symbols. Record the project, coverage caveat, and blast radius. Record a skipped reason when the server is unavailable.
5. Capture a before and after screenshot for each visual change. Save images under `docs/screenshots/`. Write `No visual result.` for a text-only change.
6. Commit with the project convention and push the branch. Find the push run with `gh run list --branch <branch> --workflow pr-quality.yml`. Watch the run to its final state.
7. Copy `~/.agents/templates/pull-request.md`. Fill every section. Add the exact run link, commit, state, observation, and check output. Remove every placeholder.
8. Create the PR with `gh pr create --title "..." --body-file <file>` plus the metadata flags. Always pass `--base <base>`. Repeat `--label <name>` and `--reviewer <handle>` for each value. Add `--milestone <name>`, `--assignee <login>`, and `--project <title>` when the project defines them. Add `--draft` while the run is pending or the project policy requires a draft. Mark an absent value as `None` in the body, never invent one.
9. Watch the pull request run to its final state. Confirm the metadata with `gh pr view <number>`. Add what is missing with `gh pr edit --add-label <name> --milestone <name>` when the project policy requires it. Update the body when the run state changes.
10. When a CI failure or a review comment gives a reusable rule, distill it in place. Workflow rules go through `github-ci-workflow`. Other rules update a skill file and pass the skill validator. Keep one-off facts in the PR notes.

Stop when the PR exists, the body is complete, the metadata matches the project, the CI state is current, the observation has evidence or a skip reason, and the lesson is recorded as a rule.

## Red Flags

- **HARD-GATE:** A failed local gate or push run blocks a ready PR. Keep the PR as a draft while the failure is open.
- **HARD-GATE:** A Codebase Memory claim needs a coverage probe. Graph results are pointers until source review confirms them.
- Do not invent screenshots, tests, CI states, graph coverage, PR links, labels, milestones, assignees, or reviewers.
- Do not add secrets, `.env` files, or unrelated files.
- Keep `--draft` whole while the PR run is still open.
- Do not use `pull_request_target` for untrusted branch code.
- Keep the workflow permission set at the smallest required scope.

## Verification

Run `python3 ~/.agents/scripts/skill-validator.py`. Expect no P0 for `push-pr`. Check that `references/pull-request-format.md` and `references/ci-and-observation.md` exist. Check the workflow with the repository YAML checker when one exists. Run `git diff --check` on the owned files. Test the PR body contract with a filled copy of `~/.agents/templates/pull-request.md`; the copy must include the GitHub metadata rows filled or marked `None`.

## Skill Result Contract

```
<skill_result>
  <skill>push-pr</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>branch, diff scope, gate output, CI run link and state, observation coverage, screenshots</evidence>
  <artifacts>filled PR body, screenshots, PR link, learn record when a lesson exists</artifacts>
  <risks>open CI failure, missing graph coverage, missing screenshot, draft PR, or none</risks>
</skill_result>
```

## References

- `references/pull-request-format.md` - fixed PR body order and evidence fields.
- `references/ci-and-observation.md` - workflow events, anti-slop checks, graph observation, and learning.
- `~/.agents/skills/github-ci-workflow/SKILL.md` - the skill that authors and reviews the workflow file.
