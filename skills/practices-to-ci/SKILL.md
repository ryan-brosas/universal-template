---
name: practices-to-ci
description: "Use when a repo has code practices/discipline that should be enforced automatically — turn them into mechanical CI checks instead of relying on prompting or prose rules."
disable-model-invocation: true
---

# Practices to CI

Turn code practices and discipline into mechanically-enforced CI checks. This
is the "steer outcomes, not behavior" principle (Pillar 2) made concrete: don't
prompt for behavior, enforce it with checks.

## The principle

- **Anything mechanical/predictable/deterministic → a CI check.** (Pillar 4)
- **"Prompting for something mechanically enforceable is useless."** Use gates
  that can't be bypassed.
- A restriction is a conclusion you earn from a real failure — the CI check
  proves the practice holds.

## What to turn into checks

From the pre-commit configs of high-quality repos:

| Practice | CI check |
|---|---|
| No trailing whitespace | grep `[ \t]+$` |
| Files end with newline | check last byte is `\n` |
| No smart quotes/ligatures | scan for `\u201c\u201d\u2018\u2019\ufb01\ufb02` |
| No large files | `os.path.getsize` > threshold |
| Valid YAML/JSON/TOML | parse each |
| No typos | lightweight codespell dictionary |
| No direct commits to main | `no-commit-to-branch` |
| No secrets committed | scan for key patterns / use gitleaks |
| No dead/unused code | lint (ruff/knip/eslint) |

## How to apply

1. **Identify the practice** the repo wants to enforce (from AGENTS.md, pre-commit
   config, or code discipline).
2. **Write a check script** (`scripts/*.py`) that mechanically verifies it and
   exits non-zero on failure.
3. **Wire it into CI** (`.github/workflows/*.yml`) so it runs on PRs/pushes.
4. **Upload failure logs as artifacts** so failures are debuggable.
5. **Fix what it catches** — a check that finds nothing is untested; verify it
   catches a real violation (test the un-fixed version).

## The pi-template's checks

- `check-integrity.py` — pack/member/router/manifest parity
- `quality-gate.py` — skill/essentials quality (duplicates, orphans)
- `repo-hygiene.py` — trailing whitespace, EOF newline, smart quotes, large
  files, mixed line endings, YAML/JSON/TOML validity, typos, secrets scan,
  forbid-submodules
- `dead-code.py` — finds unused scripts and unreferenced skill files (farmed
  from vitest's knip dead-code practice)
- `conventional-commit.py` — validates commit subjects follow conventional
  commits; `pr-title.yml` validates PR titles (farmed from graphrag's semver
  check)
- `labeler.yml` + `labeler workflow` — auto-labels PRs by changed paths
  (farmed from modelcontextprotocol's labeler)
- `security-audit.yml` — runs zizmor on workflows (farmed from pydantic-ai's
  zizmor hook) to catch insecure GitHub Actions patterns
- `stale-pr-close.yml` — closes stale PRs with a dry-run default (farmed from
  opencode's close-prs pattern)
- `stale.yml` — auto-closes stale issues/PRs via actions/stale (farmed from
  graphrag's issues-autoresolve)
- `lock-closed.yml` — auto-locks closed issues/PRs via lock-threads (farmed
  from vitest's lock-closed-issues)
- `.pre-commit-config.yaml` — local pre-commit enforcement (no-commit-to-branch,
  yaml/toml, eof-fixer, trailing-whitespace, large files, codespell) + runs
  repo-hygiene
- `.github/ISSUE_TEMPLATE/` — bug/feature/question issue templates (farmed)
- `.github/pull_request_template.md` — What/Why/Testing + verification checklist
- `.github/workflows/branch-protection.yml` — no direct PRs to main
- `SECURITY.md`, `CODEOWNERS`, `.github/dependabot.yml` — repo-level practices

## When to use

Use when a repo has a practice that "should be followed" but isn't enforced —
turn it into a check rather than adding a prose rule. This complements
`ci-best-practices` (how to write good workflows) and `code-discipline` (the
practices themselves).
