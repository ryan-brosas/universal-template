# Security baseline for GitHub Actions workflows

Treat every workflow as executable security-sensitive code. These rules are durable; verify exact current syntax and feature status against official GitHub docs when implementing — do not trust frozen snippets.

## Token permissions (least privilege)

- Default to a minimal top-level block — `permissions: contents: read` covers checkout-and-test workflows — then grant per-job writes only where a job actually writes. `permissions: {}` when nothing needs the token.
- Never `write-all`. Every granted permission must be explainable: release → `contents`/`packages`; attestation → `attestations` + `id-token`; dependency submission → `contents: read` + `write` on the submission scope per current guidance.
- Checkout with `persist-credentials: false` unless a later step genuinely pushes with the workflow token.
- `GITHUB_TOKEN` scope = the repository. Cross-repo or org effects need a scoped app/PAT — that is a signal to redesign, not to widen.

## Action pinning (supply chain)

- Pin every third-party `uses:` to a **full-length commit SHA** with the human-readable version in a same-line comment: `owner/action@<full-40-char-sha> # vX.Y.Z`. Never `@main`; treat version tags as mutable by default.
- Resolve the SHA from the action's actual upstream repository (release/tag → commit), never from a prompt or blog post. First-party `actions/*` follow the same discipline.
- Local actions (`uses: ./path`) and reusable workflows within the same repo are exempt from SHA pinning; cross-repo reusable workflows are pinned like actions.
- Keep pins maintainable via Dependabot (`package-ecosystem: github-actions` in `.github/dependabot.yml`) — it updates SHA refs and version comments. Do not build a homegrown SHA-updater.
- Before adding a third-party action ask: is native functionality enough? maintained? what permissions does it get? can a 3-line script replace it? Only add what earns its trust.

## Untrusted input

- GitHub context fields (PR/issue titles and bodies, branch names, commit messages, labels, usernames, review bodies) are attacker-controlled data. Never interpolate `${{ }}` expressions into `run:` shell. Pass through `env:` and reference as quoted shell variables; prefer action `inputs:` over raw event payloads.
- `workflow_dispatch` inputs: type them (`choice`, `boolean`); give destructive automation a `dry_run` input defaulting to true. Never let an input become raw shell arguments.
- Artifacts produced by untrusted workflows are untrusted input. A privileged job consuming an artifact must validate it, not execute it.

## pull_request_target

Privileged: runs in the base repository context with access to secrets and a writable token. Legitimate uses: labeling, metadata automation, trusted triage. The dangerous pattern — checkout of the PR head + execution + secrets — is the classic Actions compromise. HARD-GATE: never run untrusted PR code under `pull_request_target`. If privileged post-processing is genuinely needed, separate workflows: low-trust `pull_request` job produces a minimal, validated result; a trusted workflow consumes only that metadata.

## Fork PRs (public repos)

Normal fork PRs get read-only tokens, no secrets, and may require maintainer approval to run workflows — design so ordinary contributions still validate: public validation paths need no secrets; integration/deployment paths run on trusted events only. Never run fork PR code on self-hosted runners. Dependabot branches face additional restrictions — don't build CI only Dependabot can't pass.

## Secrets & credentials

- Secrets live in GitHub's secret store (environment > repository > org, narrowest ownership that works), never in YAML, never echoed, never in cache/artifact paths. Masking is a safety net, not a design.
- PR jobs get no production credentials — the workflow graph should show privilege tiers: tests (read-only) → staging (staging secrets) → production (environment-gated production secrets).
- Prefer short-lived cloud auth: OIDC federation (`id-token: write` only on the job that federates) over stored access keys. Scope the cloud trust policy to repo + environment/ref + workflow, not "any workflow in the org".

## Environments

Use GitHub environments where deployment boundaries need secrets isolation, approvals, branch restrictions, wait timers, or deployment history (staging/production). Ordinary lint/test jobs never need an environment. Deployment jobs reference the environment by name; protection rules themselves are configured by `github-repo-setup` per the handoff contract.

## Self-hosted runners

Privileged infrastructure: assume code running on them persists and can reach host credentials, Docker sockets, and cloud metadata. Public repo + fork PR + persistent self-hosted runner = critical. Ephemeral, isolated, single-use runners in a locked-down group are the only acceptable form for untrusted code — and GitHub-hosted ephemeral runners are almost always the right answer. Never add `runs-on: self-hosted` merely because a workload is slow.

## Cache & artifact trust

Caches are keyed by branch with fallback to the base branch — a low-trust workflow can poison a cache a privileged workflow later restores. Never cache secrets/keys; never execute restored cache contents as trusted code; cache miss must not break the build. Artifacts: minimum needed, retention proportional to purpose, never sensitive files, never the whole checkout.

## Workflow security scanning

- **zizmor** — the catalog standard for workflow security audit (see `.github/workflows/security-audit.yml`): dangerous triggers, template injection, credential persistence. Run it locally on any workflow you touch.
- **actionlint** — syntax/expression correctness; complements, not replaces, zizmor.
- **CodeQL** — prefer GitHub's default code-scanning setup where eligible; advanced CodeQL workflow only for real customization (custom build, matrix, query packs). GitHub can also analyze workflow files themselves where available — enable rather than stacking duplicate scanners.
- One useful scanner beats five stacked ones; every scanner is a dependency to maintain.

## Actions policies & execution protections

Org/repo/enterprise Actions policies (allowed actions, SHA-pinning requirements, actor restrictions) and ruleset workflow protections exist and evolve. A workflow that fails to start may be policy-blocked, not YAML-broken — diagnose with `gh` before editing YAML. Never weaken a security control to get green; report "workflow blocked by policy" and hand the policy decision to the repository owner. Verify current feature status in official docs — do not encode preview behavior as permanent.

## GitHub Agentic Workflows (boundary)

`.github/workflows/*.md` sources with compiled `.lock.yml` outputs are GitHub Agentic Workflows — LLM-judgment automation, not deterministic CI. Author/compile via the current `gh aw` vendor flow; never hand-edit generated `.lock.yml`. Keep agent permissions minimal (read + comment, not production write), and never let agentic judgment replace a deterministic gate: a test job decides whether tests pass; an agent may explain why coverage is missing.
