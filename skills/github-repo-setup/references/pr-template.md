# PR Template — canonical shape, risk scaling, validation, creation

## Canonical template (`.github/pull_request_template.md`)

```markdown
# Summary

What changed? One to three lines stating the user-visible result.

# Why

What problem does this solve? Reference an issue when one exists.

# Implementation

Important implementation decisions and boundaries only. Do not narrate every changed file.

# Reference / Prior Art

If external code materially influenced this change, record:

- repository and upstream URL
- component or path studied
- revision/commit when materially ported
- verdict: ADOPT / ADAPT / INSPIRATION

If none: N/A

# Verification

List only checks actually run, with results:

- unit / integration tests
- compiler / typecheck / lint / build
- JetBrains inspections or MCP Steroid semantic verification
- manual runtime verification, benchmark, CI

Local verification: state what PASSED. CI: PENDING until it runs.

If nothing applies: N/A

# UI / Visual Evidence

For frontend or visual changes: screenshot, recording, responsive states, runtime/browser evidence. Model review is not rendered proof.

If none: N/A

# Risks

Regression, compatibility, migration, performance, or security impact — or: None identified.

# Breaking Change

No  (or: Yes, with migration requirements)

# Checklist

- [ ] Relevant verification passes
- [ ] Documentation reflects changed public behavior
- [ ] Obsolete paths introduced or replaced by this change were handled
- [ ] External source and license obligations were checked when materially porting code
- [ ] No secrets or credentials were added
```

Keep the checklist this short. Never add subjective items (clean code, elegant architecture, follows best practices) — those are not mechanically meaningful; deterministic checks belong in CI (see `github-actions-engineering`).

## Detail scales with risk

| Change | Expected body |
|---|---|
| Tiny fix | one-line Summary, Verification list, everything else N/A |
| Normal feature | Implementation decisions + full Verification |
| Large refactor | affected boundaries + risk focus |
| Architecture change | rationale + considered alternatives |
| Frontend/visual | UI / Visual Evidence with real rendered proof |
| Security or performance | the specialized evidence for the claim |

A two-line fix must never require a 500-word body.

## Optional deterministic body validation

Only if the project wants it; keep it cheap and reusable:

- body is not empty; `# Summary` and `# Verification` headings exist
- template placeholder sentences were not left unchanged

Never require word counts, prose in every optional section, or LLM grading. `Risks: None identified` is a valid answer, and trivial fixes must pass.

## Creating a PR from finished work

1. Read the actual branch state: `git diff <base>...HEAD`, `git log <base>..HEAD`.
2. Verification section = only checks actually run, with outcomes. Never fabricated. Distinguish `Local verification: PASSED` from `CI: PENDING`.
3. Reference / Prior Art = sources actually consulted; record license obligations when materially porting code.
4. Push when authorized, then `gh pr create --title <conventional-title> --body-file <file>`.
5. Labels only on strong evidence (`.github/**` → `area:ci`; docs-only diff → `type:docs`); prefer path-based label automation over model guessing.
6. Do not write speculative PR prose before implementation — the PR is the post-code artifact (why, what, reference, verification, risks, migration).

## Existing contracts win

If the target repository's CI already validates a specific PR-body contract, preserve it and generate bodies in that shape. Example: universal-template's own `pr-quality.yml` requires eight fixed sections — a repo-level contract overrides this canonical template. The commit-side counterpart lives in `git-workflow-and-versioning`.
