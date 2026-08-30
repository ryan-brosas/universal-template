# Coding best practices — topic index

Route each question to **one leaf**. This index mirrors common "complete guide" outlines (structure, Git, testing, security, AI) but stays agent-native: pointers and gates, not a 700-line tutorial.

## Principles (decision hints, not behavior walls)

| Idea | Where to go | Caveat |
|---|---|---|
| DRY — one source of truth | `code-discipline` | Extract after the second copy, not before the first |
| KISS — simplest working solution | `code-discipline` | Do not ban helpers; remove dead code with gates |
| YAGNI | `code-discipline`, `code-review-and-quality` | Do not block needed prerequisites for "end-to-end" stubs |
| SOLID / separation of concerns | `code-discipline`, language foundations | OOP-specific; adapt to your stack |
| Steer outcomes, not behavior | `essentials/steer-outcomes-not-behavior.md` | Convert repeated failures into CI checks |
| Mechanical enforcement | `essentials/enforce-code-quality-mechanically.md`, `practices-to-ci` | Regex/lint/test beats prompting |

## Topic files in this skill

| Topic | Reference | Primary leaf skills |
|---|---|---|
| Naming & formatting | `naming-and-formatting.md` | `typescript-coding-standards` (TS), project linter |
| Documentation | `documentation-and-readme.md` | `templates/readme.md`, `workflow-lifecycle` init |
| Error handling | `error-handling-and-resilience.md` | `quality-gate-methodology`, `testing-anti-patterns` |
| Git & collaboration | `git-and-collaboration.md` | `push-pr`, `code-discipline` |
| AI-assisted coding | `ai-assisted-coding.md` | `agent-code-quality-gate`, `AGENTS.md` |
| Performance & data | `performance-and-data-efficiency.md` | profile first; stack-specific foundations |

## Quality stack (typical implementation loop)

```
coding-best-practices (pick topic)
        ↓
code-discipline (implement scoped)
        ↓
test-driven-development / quality-gate-methodology / testing-anti-patterns
        ↓
agent-code-quality-gate (before "done")
        ↓
code-review-and-quality (before merge)
        ↓
practices-to-ci (encode new mechanical rules)
        ↓
push-pr (ship with evidence)
```

## Security and CI (parallel tracks)

- **Security surface** → `security-and-hardening` (validate boundaries, secrets, OWASP map).
- **Workflow shape** → `ci-best-practices`, `github-ci-workflow`.
- **Catalog repo** → `AGENTS.md` gate block + `.github/workflows/pr-quality.yml`.
