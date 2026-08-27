---
name: github-ci-workflow
description: "Use when creating, updating, or reviewing the GitHub Actions CI workflow that enforces a project coding-practice and anti-slop gate. Copy templates/github-pr-ci.yml into the project as .github/workflows/pr-quality.yml, replace the AGENTS_GATE placeholder with the project AGENTS.md gate, keep least-privilege permissions and cancel-in-progress concurrency, then validate the YAML and watch one run."
disable-model-invocation: true
---

# GitHub CI Workflow

## Core Principle

One workflow shape serves every project. The shape lives at `~/.agents/templates/github-pr-ci.yml`. Each project gets its own copy with its own gate. The copy fails closed while the gate placeholder stays. The global catalog stores the skill and the template, never an active workflow.

The shape follows evidence from Codebase Memory graphs. Repos that run their gates for a long time pin actions, disable checkout credentials, cancel stale PR runs, and keep permissions minimal.

## When to Use / NOT

- **Use when:** you author a CI workflow for a project.
- **Use when:** you update an existing workflow and must keep the shape.
- **Use when:** a reviewer asks why a step exists or whether the gate is right.
- **NOT when:** the project workflow already matches the template and the gate. Leave it alone.
- **NOT when:** a one-off shell check is enough. A workflow pays for itself on every push and PR.

## Workflow

1. Read the project `AGENTS.md`. Write down the canonical gate: lint, format, type check, test, and `git diff --check`. Note the exact command and its exit contract.
2. Copy `~/.agents/templates/github-pr-ci.yml` into the project as `.github/workflows/pr-quality.yml`.
3. Replace the gate placeholder in the Run the project gate step with the project gate. The workflow fails closed while the placeholder stays.
4. Check the triggers. Keep `push`, `pull_request`, and `workflow_dispatch` unless the project needs a smaller set. Add `merge_group` when the repo uses merge queues. When you add `paths`, include `.github/workflows/**` so a workflow edit always runs it.
5. Check the security block. Keep `permissions: contents: read` and `persist-credentials: false`. Pin reviewed action versions. Keep secrets out of pull request jobs and out of the file.
6. Check the diff step. For a PR the range spans base to head. For a push the range spans the previous commit to the new head.
7. Keep the PR body contract step only when the project fills PR bodies from `~/.agents/templates/pull-request.md`. Keep the placeholder denylist whole, including the GitHub metadata rows. The metadata is set with `gh pr create`, not by a write job.
8. Validate the YAML. Run the workflow once by manual dispatch or push. Watch it to a final state.
9. When the run fails, fix the file or the failure, not the claim. When the failure names a reusable rule, write it as a check in the workflow or as a line in this skill. Record the failure, the command or code that fixed it, and the cause.

Stop when the file exists, the placeholder is gone, the YAML parses, the gate matches AGENTS.md, and one run reached a state you recorded.

## Learn in place

A failed run or a review comment is a lesson. Do not wait for an external prompt. Distill the lesson here: name the rule, write it as one line, then add it as a workflow check or as a line in this skill. When you changed the skill file, run the skill validator again. The next run enforces the rule on its own.

## Red Flags

- **HARD-GATE:** Never land a workflow under `~/.agents/.github`. Keep it in projects.
- **HARD-GATE:** The file must fail while the gate placeholder stays. Never push a file that still carries it.
- Do not weaken the permission block or `persist-credentials: false`.
- Do not give the job write access to labels, pull requests, or milestones. Metadata is set at creation time by the agent, not by the workflow.
- Do not paste secrets or `.env` values into the file.
- Do not swap the project gate for another one. AGENTS.md is the contract.
- `pull_request_target` reads the base branch with write permissions attached. Do not use it for untrusted submitters. A label script in opencode runs on it; treat every use as a reviewed exception, not a pattern.
- Do not copy the `concurrency` key with `cancel-in-progress: true` into deploy or release runs. Those runs must finish in order.

## Verification

Run `python3 ~/.agents/scripts/skill-validator.py`. Expect no P0 for `github-ci-workflow`. Read the final YAML and confirm the placeholder is gone, a gate from AGENTS.md is installed, and `concurrency` plus `persist-credentials` are present. Grep the file for the placeholder and require zero hits. Confirm the PR body check carries `## GitHub metadata` in its required headings before you report success.

## Skill Result Contract

```
<skill_result>
  <skill>github-ci-workflow</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>AGENTS.md gate, installed placeholder, YAML parse, recorded run state</evidence>
  <artifacts>project .github/workflows/pr-quality.yml, the run link</artifacts>
  <risks>placeholder left, wrong gate, missing run, leaked secret</risks>
</skill_result>
```

## References

- `~/.agents/templates/github-pr-ci.yml` starts the project workflow.
- `~/.agents/templates/pull-request.md` carries the PR body contract.
- `~/.agents/skills/push-pr/SKILL.md` watches the run and files the PR.
- The learning loop lives in the `Learn in place` section of this skill. It needs no prompt file.
