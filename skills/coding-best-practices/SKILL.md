---
name: coding-best-practices
description: "Use when starting implementation, onboarding to team standards, or asked for general coding best practices — routes topic questions to the right leaf skill (discipline, tests, review, security, CI) without restating every rule inline."
---

# Coding Best Practices — topic router

## Core Principle

General coding guidance is a **map**, not a monolith. Route each topic to one leaf skill or one mechanical gate — steer outcomes with checks, not walls of prose (see `essentials/steer-outcomes-not-behavior.md`).

## When to Use / NOT

- **Use when:** starting a coding task, answering "what are best practices for X?", onboarding someone to how this catalog expects work to flow, or choosing which quality skill to load next.
- **Use when:** the question spans naming, docs, Git, testing, security, or AI-generated code and you need the right pointer fast.
- **NOT when:** the task is language-specific TypeScript modeling — load `typescript-coding-standards` instead.
- **NOT when:** declaring work complete — load `agent-code-quality-gate` and the project gate from `AGENTS.md`.
- **NOT when:** opening or updating a PR — load `push-pr`.
- **NOT when:** authoring a new skill — load `writing-skills`.

## Workflow

1. **Classify the topic** using `references/topic-index.md` (naming, docs, errors, Git, AI, performance, principles).
2. **Load the leaf** cited on that row — never paste the whole guide inline.
3. **Implement** under `code-discipline` (scope, verification, one source of truth).
4. **Test** under `quality-gate-methodology` / `test-driven-development` / `testing-anti-patterns` as appropriate.
5. **Review** under `code-review-and-quality` before merge when human or agent review is in scope.
6. **Enforce** anything mechanical via `practices-to-ci` and the project CI gate — if it can be a check, do not leave it as a prompt.
7. **Ship** via `push-pr` when the branch is ready.
8. Stop when the topic is answered by the loaded leaf and any applicable gate has exit 0 evidence.

## Topic → leaf (quick map)

| Topic | Load first | Mechanical gate |
|---|---|---|
| Scope, verification, design taste | `code-discipline` | project CI + `agent-code-quality-gate` |
| Naming, formatting, readability | `references/naming-and-formatting.md` | linter/formatter in project CI |
| README, docstrings, comments | `references/documentation-and-readme.md` | `repo-hygiene` (catalog) |
| Errors, resilience | `references/error-handling-and-resilience.md` | behavior tests |
| Git, branches, PRs | `references/git-and-collaboration.md` | `push-pr`, conventional commits |
| AI-generated code | `references/ai-assisted-coding.md` | `agent-code-quality-gate` |
| Performance / data efficiency | `references/performance-and-data-efficiency.md` | profile-first; benchmark in CI when stable |
| Security | `security-and-hardening` | secret scan, dependency audit |
| Turn practice into CI | `practices-to-ci` | `.github/workflows/pr-quality.yml` |

## Red Flags

- **HARD-GATE:** Prompting for something mechanically enforceable instead of adding a CI check (`practices-to-ci`).
- Loading this router and then ignoring the cited leaf — the router has no rules of its own beyond routing.
- Treating DRY/KISS/YAGNI/SOLID as behavioral walls; use them as decision hints, then verify with gates (see `essentials/steer-outcomes-not-behavior.md`).
- A "best practices" answer with no named skill, no gate command, and no evidence.

## Verification

- The chosen topic row from `references/topic-index.md` names a leaf skill or reference file you actually opened.
- For implementation work: `agent-code-quality-gate` five checks recorded before claiming done.
- For catalog edits: `SKILLS_ROOT="$PWD/skills" python3 scripts/skill-validator.py` exit 0.

## Skill Result Contract

```
<skill_result>
  <skill>coding-best-practices</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>topic classified, leaf skill(s) loaded, gate output or skip reason</evidence>
  <artifacts>pointer list, verification commands run</artifacts>
  <risks>wrong leaf loaded, prose-only guidance with no gate, or none</risks>
</skill_result>
```

## References

- `references/topic-index.md` — full topic table and essentials pointers.
- `references/naming-and-formatting.md` — names, conventions, comments, whitespace.
- `references/documentation-and-readme.md` — README, docstrings, why-not-what comments.
- `references/error-handling-and-resilience.md` — errors at boundaries, tests over try/except alone.
- `references/git-and-collaboration.md` — Git, branches, commits, PRs.
- `references/ai-assisted-coding.md` — reviewing generated code, context files, no blind trust.
- `references/performance-and-data-efficiency.md` — profile first, vectorize/chunk when measured.
