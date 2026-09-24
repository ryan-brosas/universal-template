# CI evidence and structural observation

## CI evidence

The `github-actions-engineering` playbook owns workflow authoring and review. Read
the project's actual triggers, jobs and branch rules; do not assume every project
runs the same events or gates. `pull-request-format.md` owns PR presentation.

- Find runs with an explicit repository, branch and event. For a branch push:
  `gh run list --repo <owner/repo> --branch <branch> --commit <sha> --event push`.
  Pin workflow/run IDs and attempts; the same SHA in another repository or event
  is not this push's verdict. PR workflows may test a synthetic merge revision;
  record that association rather than mistaking it for the branch head.
- Watch expected checks to a terminal state before claiming success. A PR may be
  under review while CI runs; follow the parent procedure's delivery boundary.
- Record run links and observed states in the requested report or PR evidence,
  without treating a status report as permission to edit an upstream PR.
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

## Finish the observation

Once the expected checks pass and the current head is verified, report that CI
result and remaining review gaps once, then stop observing. Continue any other
work the user requested. Reopen observation for a changed head or check state,
a new failing run, or a genuinely new contradictory user report. A carried or compacted copy of the original complaint is not a new report;
assistant commentary is not user evidence.

For a new contradictory report, make one bounded check of the named PR/head/run.
If it still passes, give that revision's run link and ask which failing run the
user means instead of repeatedly polling or searching unrelated repositories.
While checks are pending, use a bounded watch and report meaningful transitions,
not repeated announcements of the same observation. If a tool detaches a watch or
a continuation interrupts its return, retain the process/run IDs and log paths.
Inspect that watch's liveness and output before starting another; a still-running
shell is not a CI success. Prefer one wait to repeated sleeps and status queries;
if the host offers no join, use bounded liveness checks without duplicating the
watch. Replace a dead watch only when the relevant run still needs observation.
Keep recovery deliberation out of progress messages, and put detailed logs in
evidence files rather than repeating the execution plan to the user.

## Structural observation

Every PR must carry revision-bound structural evidence from
`../../pre-pr-validation/README.md`. That procedure owns the required Steroid IDE
inspection, local Fovea `fovea_impact` analysis and, when the change's correctness
depends on indexed code evidence or the user requested it, the Sourcebot
`ask_codebase` baseline challenge; do not skip a required lane because a diff is
small. A BLOCKED draft/WIP PR records the unavailable lane and its coverage limits
instead, and is never relabeled READY. Source and tests confirm every structural claim. Record
the repository, revision and covered paths, and revalidate after the delivered
revision changes. A search miss is not proof that callers or consequences are
absent.

## Learnable rules

When a CI failure or review comment exposes a reusable rule, mark it as a `leverage-capture` candidate in the PR notes. The capture decision happens there — not automatically after every PR.
