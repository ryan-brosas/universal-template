---
title: github-actions-engineering
summary: 'Use when designing, creating, auditing, repairing, hardening, or optimizing GitHub Actions CI/CD: set up CI for a project, fix a failing workflow, secure or speed up Actions, define required checks, build release or reusable workflows, or diagnose a stuck required check. Owns.github/workflows/ and workflow-adjacent CI config.'
kind: playbook
---

# GitHub Actions Engineering

## Core Principle

Minimum CI that proves the project's actual requirements, with strong security boundaries and predictable GitHub integration. CI orchestrates project logic (it invokes the project's real verification surfaces); it never becomes the only place that logic exists. One strong architecture beats many workflows.

## When to Use / NOT

- **Use when:** "set up CI", "fix our workflow", "audit our Actions", "make CI faster", "secure our workflows", release/deploy automation, reusable workflows, test matrices, merge-queue or required-check trouble, Actions cost.
- **Modes:** audit (read-only findings) · create · repair · harden · optimize · reusable · release · deploy · migrate. The request picks the path; audit never mutates.
- **NOT when:** wiring rulesets/labels/templates or configuring GitHub to *require* a check (`github-repo-setup`, this skill defines and proves the check, that skill requires it). GitHub Agentic Workflows / `gh aw` / `.github/workflows/*.md` + compiled `.lock.yml` (use the current vendor agentic-workflows flow. never hand-edit generated `.lock.yml`). a failing test that fails locally too (fix the project, not CI).

Use [GitHub CLI](../github-cli/README.md) for command, auth and API mechanics, and
[CI observation](../push-pr/references/ci-and-observation.md) for revision-bound
run selection and verdicts. This playbook owns workflow design and repair.

## Workflow

1. **Inspect the project before any YAML.** Manifests, lockfiles, workspaces (`pnpm-workspace.yaml`, `turbo.json`, Cargo workspace, go.work, pyproject/uv/poetry), version sources (`mise.toml`, `.tool-versions`), task runners (Makefile/Justfile/Taskfile), existing scripts, test dirs, release/deploy config. Use the commands the project already declares (`npm run typecheck`, `just verify`, `make ci`), never reinvent them in YAML. Classify the repo type (library/app/CLI/monorepo/service/container/template/experimental/multi-language), it decides how much CI is appropriate.
2. **Inspect existing CI.** Every file in `.github/workflows/`: names, triggers, jobs, required checks, permissions, pins, caches, matrices, secrets, environments, reusable workflows, schedules. Preserve intentional architecture; never add `ci-new.yml` beside a working `ci.yml`. Classify each `uses:` reference (SHA / tag / branch / local / docker) and flag mutable ones.
3. **Define the CI contract before writing YAML.** What must be true before a change is accepted (required) vs informational (optional), derived from the project's real gates and regression history, not generic best practice. Name the stable required check (see `references/required-checks.md`); required check names are an external API once rulesets depend on them.
4. **Design the smallest architecture that satisfies the contract.** Triggers each with a reason; permissions least-privilege; one required gate; jobs split only when runtime or permissions differ; matrix only for real variation; caching only where it pays; concurrency with identity; timeouts that reflect reality. Quality level (minimal/standard/release/deployment/hardened-OSS) is inferred from the project, not chosen ceremonially.
5. **Apply the security baseline** (`references/security.md`): minimal `permissions:` (top-level `contents: read`, per-job writes), full-SHA pins with version comments, no untrusted interpolation into `run:`, `pull_request_target` treated as privileged, fork-safe PR jobs, secrets only at their boundary, OIDC over long-lived keys, self-hosted runners never for untrusted code.
6. **Implement.** Workflow YAML stays an orchestrator: checkout → setup → install → *project-defined check* → report. Multi-line logic belongs in `scripts/`, repeated step logic in composite actions, repeated job orchestration in reusable workflows, extracted only after real repetition. Start from `templates/github-pr-ci.yml` when the project wants the standard PR-gate shape (replace the gate placeholder; the file fails closed until you do).
7. **Validate.** YAML parse; `actionlint` when available (detect, don't require); the repository's configured workflow security analysis, `zizmor` locally when installed, and a specialized scanner only when justified; shellcheck via actionlint when present. If a tool is unavailable, say so, never claim it ran. Then run the project's own gates locally.
8. **Verify remote behavior within the requested scope.** Select a real run by repository, event, revision and attempt through CI observation. Use `gh run watch <run-id> --repo <owner/repo> --exit-status`; inspect failures with `gh run view <run-id> --repo <owner/repo> --log-failed`. Verify triggers, check identities, permissions, caches and artifacts. Access alone does not authorize a push or dispatch. Local syntax validation is not remote proof; report a pending or unavailable run when accurate.
9. **Report the governance handoff.** List the exact check contexts and providers proven by a real run; `github-repo-setup` consumes this contract to configure rulesets, rather than guessing names or app IDs. Release/deploy environments (name, secrets, restrictions, approvals) are specified here, configured there.

**Idempotency:** inspect → compare → reconcile. A second run creates no duplicate workflows, caches, Dependabot entries, or renames of stable checks; it reports "no changes required" per item.

## Red Flags

- **HARD-GATE:** a repository's own established quality workflow is intentional architecture, never swap, rename, or copy unrelated project gates into it without an explicit request.
- **HARD-GATE:** the template file must fail while the gate placeholder remains; never push a file still carrying it.
- `permissions: write-all`, or `contents: write` added just because checkout exists. EXTREMELY-IMPORTANT.
- Workflow-level `paths:` on a required workflow, a skipped workflow leaves the required check pending forever. Trigger always; skip jobs conditionally.
- `pull_request_target` + untrusted checkout + secrets. HARD-GATE.
- `continue-on-error: true` on a required gate; `if: always()` aggregation that succeeds despite failed `needs`.
- Interpolating `${{ ... }}` context into `run:` shell (injection), pass through `env:`.
- `cancel-in-progress` on production deploys (queue instead); concurrency groups without workflow identity.
- Mutable action refs (`@main`, bare tags) without a pinning decision; secrets or credentials in cache paths; cache as trusted artifact store.
- Fork-PR code on persistent self-hosted runners. HARD-GATE.
- Publishing on any push instead of a detected release condition; rebuilding the release artifact after verification.
- Hand-maintained CodeQL where default setup suffices; a new scanner where the repository's existing analysis already covers the finding class.
- Renaming required checks after rulesets depend on them.

## Verification

- Local: YAML parse + `actionlint` (when installed) + `zizmor .github/workflows/` (when installed) + the project's own gates, record which ran.
- Remote: the expected checks on the intended revision pass under the CI observation procedure. Read back contexts and providers from the real run; a terminal run alone is not success. Report missing remote evidence explicitly.
- Audit mode ends with prioritized findings (Critical/High/Medium/Low, each with path, impact, fix, mechanical-verifiability), not a generic checklist dump.
- Repair mode names the failing layer (parse/environment/dependency/project/permission/secret/policy/external/cancellation/required-check) and fixes that layer, citing the actual run log.


## References

- `references/security.md`, permissions, pinning, untrusted input, pull_request_target, forks, secrets, OIDC, environments, self-hosted, cache/artifact trust, scanners, Actions policies
- `references/required-checks.md`, stable gates, aggregation correctness, path-filter hazard, merge queue, draft PRs, the github-repo-setup handoff contract
- `references/release-deploy.md`, release truth, trusted publishing, artifact promotion, attestations, deploy concurrency, environments, migrations
- `references/patterns.md`, orchestrator rule, DAG economics, reusable workflows, composite vs script, matrices, caching, artifacts, monorepos, cost
- `references/ecosystems.md`, concise Node/TS, Python, Rust, Go, JVM, Elixir setup patterns (project sources win over recipes)
