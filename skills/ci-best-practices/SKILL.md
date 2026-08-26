---
name: ci-best-practices
description: "Use when writing or reviewing GitHub Actions / CI workflows — best practices farmed from high-quality repos (path filtering, concurrency, caching, aggregate gates, log artifacts, annotations)."
disable-model-invocation: true
---

# CI Best Practices

Generalizable GitHub Actions / CI best practices farmed from high-quality
open-source repos (oh-my-pi, aider, and others). These make CI fast, correct,
and debuggable.

## Path filtering (only run on relevant changes)

- Use `on.push.paths` / `on.pull_request.paths` to run a workflow only when the
  files it cares about change. Saves CI time and avoids noise.
- Use `paths-ignore` with `!` negation to always run even when other workflows
  change: `- '!.github/workflows/check.yml'`.
- Include `.github/**` in paths so workflow changes re-trigger CI.
- Include lockfiles (`package.json`, `Cargo.lock`, `bun.lock`) in paths — a
  lockfile-only change can break every job.

## Concurrency (cancel stale runs)

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
- Cancel in-progress runs when a new push/PR arrives for the same ref.
- For release runs (tag pushes), scope to a per-sha group with no cancellation
  so a later main push doesn't cancel an in-flight release.

## Aggregate release gate

- Use a `release_gate` job that `needs:` all validation jobs and only runs when
  every one succeeded:
  ```yaml
  if: ${{ !cancelled() && needs.test.result == 'success' && needs.check.result == 'success' }}
  ```
- Publishing/release is held back until the gate passes; builds run in parallel
  with the test fan-out.

## Caching (speed up deps)

- Use `actions/cache/restore@v4` + `actions/cache/save@v4` around dependency
  installs, keyed on the lockfile hash: `key: ${{ hashFiles('package-lock.json') }}`.
- Cache pre-commit, pip, npm, cargo, bazel caches.

## Debuggability

- **Upload failure logs as artifacts** so a failed run's output is inspectable:
  ```yaml
  - name: Upload log on failure
    if: ${{ failure() }}
    uses: actions/upload-artifact@v4
    with:
      name: logs
      path: /tmp/*.log
      retention-days: 2
  ```
- **Use workflow annotations** (`::notice`, `::warning`, `::error`) to surface
  important info in the run summary instead of burying it in logs.
- **Smoke-test artifacts** after download — a corrupt artifact must fail here,
  not as a confusing error downstream.

## Job hygiene

- Set `timeout-minutes` on every job (bounded, no infinite hangs).
- Set `permissions: contents: read` (least privilege) unless the job needs write.
- Use `if: ${{ !cancelled() && needs.X.result == 'success' }}` to only run
  downstream jobs when upstream succeeded.
- Prefer reusable composite actions (`.github/actions/`) for repeated setup.

## Scheduled drift checks

- Run a `schedule` cron (daily) that re-runs the full check suite, so drift is
  caught even when no PR triggers the path-filtered workflows. Farmed from
  aider's `check_pypi_version` pattern (a scheduled version-drift check).
- Use `workflow_dispatch` to allow manual triggering alongside the cron.

## Input security (critical)

- **Never interpolate `inputs.*` directly into `run:`** — a malicious input can
  inject shell. Pass inputs via `env:` and reference them as shell vars:
  ```yaml
  env:
    VERSION: ${{ inputs.version }}
  run: echo "$VERSION"
  ```
- Use `dry_run` / `dry-run` inputs (default true) for destructive automation so
  it logs what it would do without acting. Farmed from modelcontextprotocol's
  cut-release and opencode's close-prs.
- Use `workflow_dispatch` inputs with `type: choice` for enum options.

## Release gating (critical)

- **Gate publish/release on a detected condition, not any push.** A stray push
  must never publish. Use a `detect` job that resolves whether HEAD is a
  release commit (e.g. commit message, tag, release-branch merge), then gate the
  publish job on it. Farmed from vitest's publish.yml and modelcontextprotocol's
  publish-release.yml.
- Keep detection outside the Release environment (environment approval is
  job-level), so the publish job is only created after a release is detected.
- Use `if:` conditions on commit messages / branch names to scope publish to
  the exact merge commit.

## When to use

Apply these when writing or reviewing any GitHub Actions workflow. They
complement the `code-discipline` skill (how to write code) and the
`farmed-test-harness` (how to test it).
