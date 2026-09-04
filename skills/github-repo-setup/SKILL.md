---
name: github-repo-setup
description: "Use when setting up, governing, or auditing GitHub for a project: create the repository or wire origin, set description and topics, apply namespaced labels, add the PR template and issue forms, configure rulesets with required checks and merge policy, audit the remote for drift, or run a full setup across identity, governance, security, dependencies, and releases."
invocation: entry
---

# GitHub Repo Setup

## Core Principle

Inspect first, pick the smallest governance level that fits the project, change only what is missing, and verify GitHub state by reading it back. Deterministic requirements belong in GitHub mechanics (rulesets, CI, labels, templates), never in prose.

## When to Use / NOT

- **Use when:** set up GitHub for a project (new or existing); audit an existing repository's configuration; add labels, the PR template, issue forms, CONTRIBUTING, SECURITY, rulesets, required checks, merge policy, topics, or release/tag conventions.
- **NOT when:** creating or updating a PR for finished work, or handling PR review feedback, `push-pr` owns the PR lifecycle; this skill only wires what GitHub requires (e.g. the required checks that PR's CI must satisfy).
- **NOT when:** authoring GitHub Actions workflow content (`github-actions-engineering` defines the CI contract and proves the check names; this skill only wires them as required checks); local git hygiene, commits, branches, semver, changelogs (use `git-workflow-and-versioning`); the implementation work itself.

## Workflow

0. **Mode.** `audit` (read-only, zero mutation; inspect current state with `gh repo view` and `gh api`, with `scripts/github-audit.py` available as an optional aggregate diagnostic), `setup` (additive/reconciliatory), `minimal`, `team`, or `full` (only on explicit request, e.g. "full setup"). Default: "set up" → `setup`; "audit" → `audit`.
   `full` means: inspect every GitHub surface that can earn its place for THIS project, configure the ones that do, delegate CI/version work to their owners, read back, then close with the per-surface report and decision log (`references/setup-matrix.md`). It never means turning every feature on.

   Baseline requests ("standard setup", "our baseline", "make this production-ready", "OSS-ready") select the mode from the maturity class in `references/setup-matrix.md`. Baseline requests ("standard setup", "our baseline", "make this production-ready", "OSS-ready") select the mode from the maturity class in `references/setup-matrix.md` and compose the standard baseline: `project-bootstrap` first, then this skill, then `github-actions-engineering`, then `git-workflow-and-versioning` only when the project is versioned, then the audit re-run. A plain "start a new project" requests none of this and stays with `project-bootstrap`.
1. **Preflight.** `gh --version`, `gh auth status` (record the authenticated account; an auth failure stops the run), `git status`, `git remote -v`. Determine repository existence with `gh repo view` from the repo root. A confirmed not-found is a normal result: continue to step 3 when creation was requested. Any other failure (auth, permission, network) stops and reports. HARD-GATE: if `origin` exists and is not the target repository, stop and report the conflict, never replace it.
2. **Discover facts.** Name (directory/manifest), one-sentence description candidates (README, manifest), languages and frameworks (manifests), license file, existing `.github/`, CI jobs (`.github/workflows/` + `gh api repos/OWNER/REPO/actions/workflows`), solo vs team (contributors, org teams), existing labels/templates/rulesets. Classify findings KEEP / ADD / UPDATE / REMOVE; preserve everything intentional. HARD-GATE: never choose or change a license for the user, report a missing license.
3. **New repository** (only absent and requested). Propose the name; ask only when owner or visibility is ambiguous or externally consequential, visibility is never changed silently. `gh repo create OWNER/NAME --public|--private -d "desc"`, then add `origin` only when no conflicting remote exists. Do not push unreviewed work beyond the requested scope.
4. **Metadata.** Description = one factual sentence (what it is plus its differentiator; no marketing). Topics: 5–10 lowercase, derived from real domain/language/framework/integrations; `gh repo edit --add-topic ...`.
5. **Labels.** Namespaced `type:` and `area:` (from real paths only), `priority:` only if prioritization exists, a minimal special set. Idempotent upsert: `gh label create <name> --color <hex> --description "..." --force`. See `references/labels.md`.
6. **Templates.** PR template from `references/pr-template.md`, unless the repo's CI already enforces its own PR-body contract, then preserve that and skip. Issue forms `bug.yml` / `feature.yml` / `config.yml` sized to the project. CONTRIBUTING only when a contribution surface exists. SECURITY only where a private reporting path matters (never invent an email, report the gap). CODEOWNERS only with real ownership. HARD-GATE for solo repositories: no CODEOWNERS, no required approvals.
7. **Security and dependencies (full).** Audit, then enable what the project earns: Dependabot alerts, Dependabot security updates, secret scanning and push protection, private vulnerability reporting (SECURITY.md points at it), CodeQL default setup (prefer GitHub-managed default setup over a custom workflow; a custom workflow is `github-actions-engineering` work). Configure Dependabot for every ecosystem present - for SHA-pinned Actions, `package-ecosystem: github-actions` is what keeps the pins maintainable. Report plan-unavailable surfaces as unavailable, never as enabled. See `references/security.md`.
8. **Releases (full).** Establish the release authority with `git-workflow-and-versioning` (tag + generated notes is the default), wire `.github/release.yml` to the label taxonomy, protect version tags with a ruleset (blocking deletion and update. account for moving major-version tags before restricting creation), and consider immutable releases only when published artifacts must stay fixed. The release workflow itself is `github-actions-engineering` work. See `references/releases.md`.
9. **Governance.** Prefer rulesets over legacy branch protection. Required checks come from discovered real CI jobs only, HARD-GATE: never invent a check name; with no CI, scaffold via `github-actions-engineering` when in scope, else report that required checks cannot be configured. Solo baseline: PR required + required checks + block force-push and deletion, zero required approvals. Team: add approvals, conversation resolution, CODEOWNERS where ownership is real. Merge policy: one understandable default (squash for most), preserving intentional merge-commit or rebase setups. Apply via `gh api`, then GET the ruleset back and verify targets, rules, and bypass actors, HARD-GATE: a successful POST is not a configured ruleset until read back. See `references/governance.md`.
10. **Report.** Close with the structured report in `references/setup-matrix.md` (Repository, Mode, per-surface Configured/Preserved/Skipped-with-reason, Needs decision, Verification), and read the relevant GitHub surfaces back to show zero unintentional gaps. Unresolved decisions go in "Needs decision", never buried in prose.

**Idempotency:** every step is inspect → compare → change only if necessary. A second run on a configured repository reports "No changes required" for anything already correct, no duplicate labels, templates, or rulesets.

## Red Flags

- Choosing or changing a license, visibility, owner, or default branch without explicit user intent. HARD-GATE.
- Overwriting an unrelated `origin`. EXTREMELY-IMPORTANT.
- Inventing required-check names or CI jobs that do not exist. HARD-GATE.
- CODEOWNERS (`* @owner`) or mandatory external approval in a solo repository. HARD-GATE.
- Deleting a label that carries open issues or PRs without migrating it first.
- Fabricated verification in a PR body; claiming CI passed without evidence. HARD-GATE.
- Release automation or tags for an unversioned project; a tag per PR.
- Treating a successful API POST as configured, read back or it did not happen.
- A 40-label taxonomy; bureaucracy for a tiny change.

## Verification

- `gh api repos/OWNER/REPO/rulesets` lists the intended ruleset with `enforcement: active` and the expected rules.
- Direct `gh repo view`, `gh api`, workflow, label, and ruleset reads show no unintentional gaps after setup.
- `gh label list --limit 1000 --json name` matches the intended set exactly, with no duplicates (the default fetches only 30 labels, always pass an explicit limit).
- `gh repo view --json description,repositoryTopics` reflects the metadata. Caveat: `gh repo view --json` accepts a fixed field allowlist, merge settings are NOT fields; read them via `gh api repos/OWNER/REPO --jq '.allow_squash_merge, .allow_merge_commit, .allow_rebase_merge'` (verified on gh 2.98.0).
- Local `.github/*.yml` parses as YAML.
- Re-run the skill: every already-correct item reports "No changes required".


## References

- `references/pr-template.md`, canonical PR template, risk scaling, body validation (PR creation itself is `push-pr`'s; this reference defines what GitHub governance expects of the body)
- `references/labels.md`, label taxonomy, colors, idempotent sync commands, default-label reconciliation
- `references/governance.md`, verified gh command inventory, ruleset create and read-back, solo vs team policy, releases, guardrails
- `references/setup-matrix.md`, mode and project-type matrix (including `full` and the maturity classes), the standard-baseline composition, final report format, acceptance cases
- `references/account-defaults.md`, account/organization `.github` default community files, precedence, org-level future path, authorization boundary
- `references/security.md`, security and dependency surfaces: verified endpoints, enable order, plan-availability caveats
- `references/releases.md`, release authority options, `.github/release.yml`, tag rulesets, immutable releases, attestations
