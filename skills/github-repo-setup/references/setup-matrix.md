# Setup Matrix — modes, project types, report, acceptance

## Modes

| Mode | Mutates | Adds | Deliberately skips |
|---|---|---|---|
| `audit` | nothing | remote drift report (`scripts/github-audit.py`) + graded findings (HIGH / MEDIUM / LOW) with specific proposals | everything |
| `setup` | additive + reconciliatory | description, topics, labels, PR template, issue forms, CONTRIBUTING/SECURITY when justified, ruleset from real CI | destructive changes, license decisions |
| `minimal` | additive, smallest | description, topics, core labels, PR template, CI-based default-branch protection | issue forms beyond the basics, CODEOWNERS, Dependabot, release automation |
| `team` | additive, stronger | + required approval(s), conversation resolution, CODEOWNERS (real ownership), SECURITY, dependency automation | activating team controls without evidence of a team |
| `full` | additive + reconciliatory across all surfaces | everything from `setup` plus security features, Dependabot ecosystems, release authority + release notes + tag protection, feature decisions with reasons | any feature that does not earn its place for THIS project (each skip is stated with its reason in the decision log) |

## Maturity classes (decide surfaces, not feature counts)

| Class | Configure |
|---|---|
| Experimental | description, topics, minimal CI, light PR policy; no release bureaucracy, no community files |
| Internal application | CI, ruleset, dependency + security automation, deployment governance; no public community files |
| Public OSS | metadata, topics, issue forms, CONTRIBUTING + SECURITY, vulnerability reporting, SUPPORT (or account default), labels + auto-labeling, ruleset, Dependabot, release notes; Discussions only when a community actually forms |
| Distributed library / CLI | everything from public OSS plus: versioned releases, release notes, tag protection, immutable releases when assets must stay fixed, provenance only where it adds value |

`full` classifies the project first, then configures the intersection of the class and what the repository actually uses. Every deliberate skip is recorded with a reason; "maximize GitHub" means maximizing useful integration, not feature count.

## Standard baseline (composition contract)

The "standard setup" is not a skill and not a fixed file set. It is this
composition, applied at the maturity class the project actually is:

```
project-bootstrap               scaffold or onboard (the local project exists first)
github-repo-setup               setup | full at the class-derived profile below
github-actions-engineering      CI that proves the project's real gates
git-workflow-and-versioning     only when the project is versioned
github audit                    github-audit.py re-run plus ruleset read-back
```

Requests that authorize the baseline: "create this repo with our standard
setup", "start a new project using our baseline", "make this
production-ready", "make this OSS-ready", "give this repo the full setup".
A plain "start a new project" or "create a scratch project" stays
bootstrap-only: no remote, labels, rulesets, SECURITY, or release machinery
unless separately requested.

Profile mapping (request intent to class; every row still passes project
applicability checks):

| Request | Class | Baseline adds beyond bootstrap |
|---|---|---|
| "scratch project" | experimental | nothing remote; local CI only if asked |
| "standard setup", "our baseline" | internal application | description/topics, core labels, PR template, CI plus ruleset, dependency and security automation |
| "OSS-ready", "production-ready" for a public project | public OSS | plus issue forms, CONTRIBUTING, SECURITY with private vulnerability reporting, SUPPORT (or account default), auto-labeling |
| "full setup" for a versioned library/CLI/Action | distributed | plus release authority, tag protection, generated release notes, immutable releases only where published artifacts must stay fixed |

Existing repositories are reconciled: inspect, compare, change only what is
stale or missing, and preserve intentional labels, established CI, release
strategy, docs, and history. Never rebuild a working repository to match this
catalog's defaults.

## Account- and organization-level defaults

Generic community files (CONTRIBUTING, SECURITY, SUPPORT, Code of Conduct,
issue/PR templates, discussion forms, FUNDING) can live once in the account or
organization `.github` repository instead of per repository. Verified facts,
precedence rules, and the boundary for touching that repository:
`references/account-defaults.md`.

## GitHub template repositories (separate mechanism)

A GitHub template repository seeds starter code, directory structure, and
common local files. It does not configure labels, rulesets, remote security
settings, metadata, or release settings; `github-repo-setup` owns those remote
surfaces either way. This catalog repository is agent configuration, not an
application template.

## Project-type adjustments

| Type | Priorities |
|---|---|
| Library | compatibility, release/versioning, public-API tests, release notes |
| Application | build/deploy CI, environment safety, UI evidence for visual changes |
| CLI | build, tests, release artifacts and versioning when distributed |
| Experimental | governance stays minimal |
| Template repository | confirm the GitHub template-repository setting is actually wanted (`gh repo edit --template`) |
| Public open source | CONTRIBUTING, SECURITY, useful issue forms, license present, good-first-issue workflow |

## Final report format (every run closes with this)

```
GitHub Setup
Repository:  owner/name
Mode:        setup | audit | minimal | team
Configured:  topics (7) · 9 labels · PR template · bug+feature forms · default-branch ruleset · required checks [quality]
Preserved:   existing MIT license · existing release workflow · custom PR-body contract
Skipped:     CODEOWNERS (solo repository) · Dependabot (not useful here) · release automation (project is unversioned)
Needs decision:  no LICENSE file — which license, if any?
Verification:    ruleset re-read (enforcement active) · label set matches · .github YAML valid
```

In audit mode replace Configured with graded findings: HIGH (correctness/security/governance problems), MEDIUM (useful improvements), LOW (polish) — each with a specific proposed change. Report by usefulness and risk, never as a giant checklist.

## Acceptance cases

| Case | Request | Expected behavior |
|---|---|---|
| A | "Set up GitHub for this project" (new solo CLI) | inspect, create if requested, description/topics, lightweight labels, PR template, ruleset from real CI, no approvals, no fake CODEOWNERS, no release automation unless versioned |
| B | "Improve our GitHub setup" (existing team app) | preserve intentional settings; audit labels/templates/rules; add missing useful controls; never recreate the repository |
| C | "Audit our GitHub setup" | zero mutation; graded findings + specific fixes |
| D | frontend repository | PR template carries the visual-evidence section; no UI correctness claims without rendered proof |
| E | repository without a license | report the gap; never invent one |
| F | origin points elsewhere | stop and report the conflict; never overwrite |
| G | run the skill twice | idempotent; second run reports "No changes required" for configured items |
| H | "Create a PR for this work" | body generated from the actual diff and checks actually run; Local PASSED vs CI PENDING distinguished |
