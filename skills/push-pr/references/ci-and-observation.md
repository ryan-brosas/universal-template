# CI, anti-slop gate, and the Codebase observation

## Workflow contract

The `github-ci-workflow` skill authors or reviews the project workflow file. It copies `~/.agents/templates/github-pr-ci.yml` into the project and replaces the placeholder gate with the project gate from AGENTS.md. The file itself lives in the project, never in the global catalog.

The workflow runs on branch pushes, pull requests, and manual dispatch. The manual dispatch is what an agent uses to watch one run before filing the PR.

The quality job uses least-privilege read access. It checks the project gate, changed-line whitespace, and the PR body contract. The PR body check requires the fixed headings, including `## GitHub metadata`, and rejects template placeholders.

## Anti-slop gate

Run the project gate from `AGENTS.md`. Use `agent-code-quality-gate` for scope, duplication, behavior tests, verification evidence, and regressions.

Record the exact command and exit status for each check. Run `git diff --check` on the branch range. Keep the diff limited to the requested change. Keep new tests active. Explain a removed test in the PR body.

The GitHub workflow is part of the gate. Review its trigger, permission scope, action versions, changed-line range, and body check. Keep untrusted code on `pull_request`. Keep secrets out of pull request jobs.

## Codebase observation

Run the graph sequence in the agent session:

1. Check Codebase Memory index status for the selected project.
2. Check coverage for every touched path with `check_index_coverage`.
3. Search changed symbols with `search_graph` or `search_code`.
4. Trace callers and callees with `trace_path` when a symbol has a blast radius.
5. Read the relevant source and tests. The graph is a map. Source and tests confirm the result.

Write one observation in the PR body. Include the project name, covered paths, parse or skip caveats, and the observed blast radius. Use a skip line when Codebase Memory is unavailable. Do not turn a missing index into an exhaustive claim.

## Learning loop

A failed check or a review comment can expose a reusable rule. Distill it in place. No prompt file is needed.

1. Write the failure as one line, the exact command or code that fixed it, and the friction cause.
2. Prefer a mechanical check. When the rule fits the workflow, author it with the `github-ci-workflow` skill.
3. When the rule fits the skill, update the matching SKILL.md and run `python3 ~/.agents/scripts/skill-validator.py`.
4. Record the rule, the changed file path, and the verification result.

Keep one-off facts in the PR notes. The rule lives in the workflow or in the skill, not in a prompt.
