# Required checks, triggers, and the governance handoff

## The CI contract

Before any YAML, write down what must be true before a change is accepted:

```
Required:  format · lint · typecheck · test · build   (from the project's real gates)
Optional:  compat matrix · benchmarks · nightly fuzz · experimental runtime
```

Derived from actual project requirements, existing verification commands, and known regression classes — never from generic best practice. The contract determines workflow count, jobs, and the required check name.

## Required checks are an external API

Once a ruleset requires a check name, renaming it breaks merges. Prefer one stable aggregate gate per workflow (e.g. job id `required`, displayed as `quality / required`) whose dependencies carry the real checks. Individual jobs may be restructured inside without touching branch rules.

### Correct aggregation job

A gate succeeds **only when every needed job reports `success`** — `if: always()` alone is wrong because it runs the gate but does not make it fail:

```yaml
required:
  needs: [lint, typecheck, test, build]
  # run even when an upstream job failed (so the verdict is visible),
  # but succeed only if every required dependency succeeded:
  if: ${{ !cancelled() && needs.lint.result == 'success' && needs.typecheck.result == 'success' && needs.test.result == 'success' && needs.build.result == 'success' }}
  steps:
    - run: echo "all required checks passed"
```

For many dependencies, generate the condition or check `needs.*.result` in a script step that exits non-zero on any `failure`/`cancelled` result — but never a gate that succeeds unconditionally.

Test the gate both ways: break a required job → gate red; fix it → gate green. A gate that never failed is not proven. Never use a required gate with plain `continue-on-error` upstream: a skipped/failed dependency must never yield a green gate. Do not add an aggregator at all when the repository's ruleset already requires stable individual checks cleanly.

Which name GitHub surfaces as the required check (job id vs display name, `workflow / job` format) must be read back from a real run (`gh pr checks`, check-runs API) before reporting the contract — see the handoff below.

## Workflow-level path filters vs required checks

A workflow skipped entirely (workflow-level `paths:`, branch filters) leaves its required check in a pending/no-status state and can block the PR forever. For a required workflow:

- **Do not** put workflow-level `paths:` on it.
- Trigger always; conditionally skip the expensive *jobs* (`if: !contains(github.event.pull_request.labels.*.name, 'ci-full')` or changed-file detection inside a step), but always emit the stable required result.
- Include `.github/workflows/**` in *non-required* workflows' paths so workflow edits re-trigger them.
- Monorepos: the same rule — an affected-package detector may skip jobs, never the required gate itself.

Verify the exact skip/pending semantics against current GitHub docs when implementing; this is the single most common way CI silently wedges a repo.

## Triggers, each with a reason

| Trigger | Use for | Notes |
|---|---|---|
| `pull_request` | PR validation | read-only context, fork-safe — the default CI trigger |
| `push` (main) | default-branch verification | catches direct pushes; required for deploy-on-merge |
| `workflow_dispatch` | manual run/recovery | typed inputs; never freeform shell args |
| `schedule` | time-dependent work | dependency health, nightly compat; runs from the default branch — verify current semantics |
| `merge_group` | merge queue | ONLY when the repo uses the merge queue — see below |
| `release` / tag push | release automation | one coherent source of release truth (`release-deploy.md`) |
| `pull_request_target` | privileged metadata only | see `security.md` — treat as dangerous |

Do not stack triggers without a reason. `on: [push, pull_request]` on a workflow that also has `workflow_dispatch` for recovery is fine; seven triggers is design debt.

## Merge queue

If the repository uses GitHub's merge queue and requires Actions checks, the required workflow must also run for merge-group events — otherwise every queued PR waits forever. Confirm with `github-repo-setup` whether a merge queue exists, add the current merge-group trigger, and verify one queued entry actually receives the required status. Do not add merge-group triggers where no queue exists.

## Draft PRs

If expensive CI skips drafts (`if: github.event.pull_request.draft == false`), verify that marking the PR ready-for-review re-fires the required workflow (current GitHub semantics: `ready_for_review` activity re-triggers `pull_request`; confirm before relying on it). A required check that stays green from an earlier skipped-draft state is a false pass — test the draft → ready transition on a real PR.

## Job naming

- Stable machine ids (`lint`, `test`, `build`); descriptive display names are fine and do not affect required-check identity — but know which one GitHub surfaces and validate from a real run.
- No emojis in required check names; they complicate ruleset matching.
- Required checks that exist only on one workflow must keep that workflow's name stable too (the check string includes it).

## Governance handoff (github-repo-setup)

This skill **defines and proves** check names; `github-repo-setup` **configures** them as required status checks in rulesets and sets merge policy. The contract this skill reports:

```
Required check contract (proven by run <link>):
  - quality / required        (aggregate gate)
Optional/informational:
  - compat / <matrix entries>
  - security / dependency-review
Merge queue: yes/no — merge-group trigger present/absent
Environments to protect: <name> (secrets, reviewers, branch restrictions)
```

`github-repo-setup` consumes exactly these strings — never invent check names on either side (its HARD-GATE). Environments, approval rules, and Actions policies are configured by that skill from this spec; do not silently assume environment protection exists.

## Quality levels (infer, don't ask)

- **MINIMAL** — build+test (+lint/typecheck if they exist), one required gate, read-only permissions. Small projects, experiments.
- **STANDARD** — full validation, caching where it pays, concurrency, pinned actions, Dependabot actions ecosystem.
- **RELEASE** — + artifact build, version/tag integration, publishing, provenance where useful.
- **DEPLOYMENT** — + environments, OIDC/secrets at the boundary, serialization, protection handoff.
- **HARDENED OSS** — fork-safe CI, dependency review, CodeQL where eligible, strict pinning.

Risk decides what is nightly vs per-PR: critical regression checks are never demoted to nightly to save minutes.
