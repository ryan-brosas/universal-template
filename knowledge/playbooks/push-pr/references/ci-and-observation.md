# CI evidence and structural observation

## CI evidence

The `github-actions-engineering` skill authors/reviews the project workflow. The workflow runs on branch pushes, pull requests, and manual dispatch; least-privilege read access; checks the project gate and changed-line whitespace. It does not parse the PR body; `pull-request-format.md` owns that contract.

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

## A fresh head has no verdict yet

An empty or partial rollup is not a pass. `mergeStateStatus: CLEAN` can appear
before the required jobs register. Bind the verdict to the revision being delivered:

- Compare `gh pr view <n> --json headRefOid,statusCheckRollup` with the pushed SHA.
  A changed head invalidates the previous verdict; do not merge an unchecked head.
- Derive expected check names and providers from the project workflows and branch
  rules, not from whichever checks currently appear. If that set is empty or
  unavailable, establish the [CI contract](../../github-actions-engineering/references/required-checks.md)
  before declaring success. An intentionally CI-free project must be reported as
  such, with its applicable local gates, not as having passed CI.
- Read states with `gh pr checks <n> --json name,state,bucket,link`; pending checks are
  not success and the command exits `8` while pending. That output carries no provider
  identity, so when a name is shared across providers confirm the expected one from the
  paginated rollup or the check-runs API (`app.slug`) and match name and provider. Wait
  for every expected
  check to be present and terminal on that head, then require a passing verdict;
  failed, cancelled or unexpectedly skipped checks are not green. Apply the
  superseded-run rule above rather than accepting an older success over a new run.
- Bound the wait. A missing check may never run: report the missing names and
  investigate triggers or policy instead of declaring success or polling forever.

## Structural observation (conditional)

Structural observation is **evidence-driven, not mandatory**. Use the active
project's IDE/LSP or Fovea (`fovea_impact`) for precise local symbol and type
questions; skip these optional tools when direct reading settles the question.
Use Sourcebot's `ask_codebase` through `../../cross-repo-source/README.md` for broad
unresolved code questions when indexed evidence can inform correctness, or when
the user explicitly requests it. The Sourcebot applicability decision belongs to
`../../pre-pr-validation/README.md`: record why it applies or does not, rather
than forcing a call because a delivery phase began. Figma/Paper-only work uses
live design evidence instead.

Source and tests confirm every structural claim. Record the repository, revision, and covered paths; do not turn a search miss into an exhaustive claim.

## Learnable rules

When a CI failure or review comment exposes a reusable rule, mark it as a `leverage-capture` candidate in the PR notes. The capture decision happens there — not automatically after every PR.
