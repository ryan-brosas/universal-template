# Workflow architecture & performance patterns

## CI as orchestrator

```
checkout → setup → install → project-defined check → report
```

The workflow invokes the project's real verification surfaces (`npm run typecheck`, `just verify`, `make ci`, `cargo test`). 150 lines of Bash inside `run:` blocks is project logic trapped in YAML — move it to `scripts/` so local developers and CI run the same code (prevents CI drift). Do not introduce a new wrapper (`just verify`) purely for uniformity; only when it genuinely unifies local+CI entrypoints.

If it can be a repository setting, Dependabot config, CodeQL default setup, environment protection rule, project script, or existing job — it should NOT be new workflow YAML. Lowest-maintenance correct mechanism wins.

## Job DAG economics

Every job pays runner startup + checkout + setup. Jobs split when one of these actually differs: runtime profile, permissions, runner OS, failure semantics, caching needs. Lint/typecheck/test each taking 20s with identical setup belong in ONE job. Splitting to look organized costs minutes on every push.

```
lint ──┐
types ─┼── required (aggregate gate; see required-checks.md)
test ──┤
build ─┘
```

## Concurrency

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.sha }}
  cancel-in-progress: true   # PR CI: yes — cancel obsolete runs
```

- Include workflow identity in every group so workflow A can never cancel workflow B (`${{ github.workflow }}-...`).
- PR CI: cancellation usually right. Deployments: `cancel-in-progress: false` (queue) — cancelling a production deploy mid-flight is dangerous.

## Matrices

Only for real variation: supported runtimes, OSes the product actually targets, architectures, DB versions. No cosmetic matrices. Tune per purpose: compatibility suites want `fail-fast: false` (see every failure); huge expensive matrices want bounded parallelism; experimental versions may be `continue-on-error` **only if explicitly informational and labeled** — a supported version never silently continues on error.

## Caching

- Prefer the ecosystem setup action's built-in dependency caching (verify current capability before relying on it) over hand-rolled `actions/cache` YAML.
- Cache = regenerable derived data keyed by what invalidates it (OS/runtime + package manager + **lockfile hash**). Never key on branch alone; avoid restore-keys so broad that stale incompatible state masquerades as valid.
- Cache is NOT persistent storage and NOT a trusted distribution channel: no secrets/keys in cached paths; low-trust workflows must not be able to poison caches privileged jobs execute; a miss must not break the build.
- Artifacts are for outputs that transfer between jobs or need retention (binaries, reports, failure logs). Set retention proportional to purpose (PR logs: days; release assets: the release system). Upload failure logs on `if: failure()` for diagnosis; smoke-test artifacts after download.

## Reusable workflows & composite actions

| Abstraction | Use for | Extract when |
|---|---|---|
| Reusable workflow (`workflow_call`) | repeated **job-level** orchestration across workflows/repos | the same job shape repeats with stable inputs |
| Composite action | repeated **step-level** logic within/across workflows | the same step sequence repeats |
| Local script (`scripts/`) | complex deterministic logic | always preferable to long inline `run:` |

- Define typed inputs, explicit secrets, outputs. `secrets: inherit` expands trust to everything — named secrets unless inheritance is deliberately justified.
- Cross-repo reusable workflows are an API: stabilize inputs/outputs/secret names; pin consumed versions; never silently break consumers. Centralize only after real repetition — a bad shared workflow multiplies failures across every consumer.

## Monorepos

Inspect the workspace manager and dependency graph before designing: small monorepo → run the whole suite (simplest); large independent packages → affected-package detection (changed files → affected units) with the required gate always emitting status; dependency-aware tooling (Turbo/Nx/Cargo workspace/go.work) → use its native task graph and remote caching rather than reinventing dependency analysis in YAML. Never one workflow per package by default; never let path filtering remove the required gate (see `required-checks.md`).

## Service containers

Tests needing Postgres/Redis/etc. run them as service containers with health probes (`options: --health-cmd ...`), never `sleep 30`. Keep infrastructure proportional to what tests genuinely require.

## Runtime, cost & storage

- Measure before optimizing: `gh run list`/`gh run view` for queue vs setup vs test time; attack the actual bottleneck.
- Cheapest runner that meets the requirement (Ubuntu default; Windows/macOS only for real platform needs). Self-hosted only with the security review from `security.md`.
- Cancel obsolete PR runs (concurrency above); bound retention; avoid redundant matrices and duplicate installs; scheduled workflows only for time-dependent work.
- Correctness is never traded for minutes.

## Workflow file organization

A small catalog: `ci.yml`, `release.yml`, `deploy.yml`, an optional workflow-security audit (zizmor) where the repository wants it, `dependency-review.yml` where justified. Not seven micro-workflows — separate only when triggers/permissions/runtime genuinely differ. Stable human-readable workflow `name:` (it appears in required check strings and the UI).

## Comments

Explain WHY, not what. `# Keep this workflow trigger broad: this job is a required status check; use job-level paths instead` — not `# Checkout repository`.

## Generated workflow hygiene

Multi-line shell: safe quoting, explicit failure behavior, no swallowed errors (`|| true` only when failure is informational), no untrusted interpolation. Prefer a repo script over a heredoc longer than ~15 lines.

## Reusable workflow promotion ladder

Do not centralize CI on first sight. The ladder:

1. First occurrence: the repository keeps its own workflow in `.github/workflows/`.
2. Repeated stable pattern: consider a reusable workflow only after enough
   repositories prove the inputs are stable, the outputs are stable, the
   security model (secrets, permissions, `github_repository` scope of callers)
   is understood, and per-project differences stay manageable as inputs.
3. Promoted: the reusable workflow lives with an owner; callers pass only real
   inputs, never project logic.

Skip promotion while any of those is unproven; duplicated-but-local beats
premature central infrastructure.
