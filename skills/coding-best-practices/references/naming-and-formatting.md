# Naming and formatting

## Names

- **Reveal intent.** Prefer `account_balance` over `ab`; function names over opaque `process()`.
- **Follow the language community.** Python/Ruby: `snake_case` variables/functions, `PascalCase` classes. JS/TS/Java/C#: `camelCase` members, `PascalCase` types. Constants: `SCREAMING_SNAKE` where idiomatic.
- **Be consistent within the repo.** Mixed conventions signal drift — enforce with the project formatter/linter (`practices-to-ci`).

## Comments

- Explain **why**, not what the code already says. If you need a what-comment, rename or extract first.
- Reserve comments for: non-obvious business rules, workaround context (+ ticket/link), external references, searchable `TODO(name):` with owner when work is deferred.
- Do not comment instead of structure.

## Whitespace and layout

- Group related statements; blank line between logical blocks (like paragraphs).
- Let the formatter own indentation and line breaks — do not hand-fight style in review.

## Mechanical gates

| Check | Typical tool |
|---|---|
| Trailing whitespace, EOF newline | `repo-hygiene.py` (catalog), pre-commit |
| Formatting | `ruff format`, `prettier`, `gofmt`, project CI |
| Import order / unused symbols | language linter |

## Leaf skills

- General discipline: `code-discipline`
- TypeScript naming/types: `typescript-coding-standards`
- Encode new rules: `practices-to-ci`
