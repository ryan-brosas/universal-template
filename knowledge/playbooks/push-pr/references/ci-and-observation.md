# CI evidence and structural observation

## CI evidence

The `github-actions-engineering` skill authors/reviews the project workflow. The workflow runs on branch pushes, pull requests, and manual dispatch; least-privilege read access; checks the project gate, changed-line whitespace, and (when the project uses a PR body contract) the body headings.

- Find runs: `gh run list --branch <branch>`; watch to a terminal state before filing or updating the PR.
- Record run links and final states in the PR body — never a claimed state you did not watch.
- Review the workflow itself as part of the gate: triggers, permission scope, action pins, untrusted code on `pull_request`, secrets kept out of PR jobs.

## Structural observation (conditional)

Graph observation is **evidence-driven, not mandatory**. Reach for Codebase Memory (`check_index_coverage` → `search_graph`/`trace_path`) when the change is structurally complex and a blast-radius claim adds value; reach for Fovea (`fovea_impact`) for local structural questions. Skip silently when the change is small or direct reading settles it — a skip needs no justification line.

When used: the graph is a map; source and tests confirm. Record the project, covered paths, and caveats. Do not turn a missing index into an exhaustive claim — and do not cite a graph you did not verify covers the code.

## Learnable rules

When a CI failure or review comment exposes a reusable rule, mark it as a `leverage-capture` candidate in the PR notes. The capture decision happens there — not automatically after every PR.
