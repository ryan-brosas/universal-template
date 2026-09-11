# CI evidence and structural observation

## CI evidence

The `github-actions-engineering` skill authors/reviews the project workflow. The workflow runs on branch pushes, pull requests, and manual dispatch; least-privilege read access; checks the project gate, changed-line whitespace, and (when the project uses a PR body contract) the body headings.

- Find runs: `gh run list --branch <branch>`; watch to a terminal state before filing or updating the PR.
- Record run links and final states in the PR body — never a claimed state you did not watch.
- Review the workflow itself as part of the gate: triggers, permission scope, action pins, untrusted code on `pull_request`, secrets kept out of PR jobs.

A check name can carry several runs on one commit. When concurrency cancels
superseded runs — a body edit, reopen, or synchronize re-fires the workflow —
the older runs remain `cancelled` in the rollup while the newest run holds the
verdict. Select the latest run per check name and provider (app ID or integration
identity when available); identical names from different providers are not
interchangeable. A `cancelled` entry that a later run of that same check superseded
is not a failure and does not make the PR unclean.

When reading raw GraphQL `statusCheckRollup.contexts`, follow
`pageInfo.hasNextPage` and `endCursor` through every page before evaluating the
rollup. A partial page is not evidence that all checks passed.

## Structural observation (conditional)

Structural observation is **evidence-driven, not mandatory**. Use the active project's IDE/LSP or Fovea (`fovea_impact`) for precise local symbol and type questions. Use the indexed source capability (`../cross-repo-source/README.md`) when a change crosses repositories and a blast-radius claim adds value. Skip silently when the change is small or direct reading settles it — a skip needs no justification line.

Source and tests confirm every structural claim. Record the repository, revision, and covered paths; do not turn a search miss into an exhaustive claim.

## Learnable rules

When a CI failure or review comment exposes a reusable rule, mark it as a `leverage-capture` candidate in the PR notes. The capture decision happens there — not automatically after every PR.
