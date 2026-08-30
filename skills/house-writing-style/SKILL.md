---
name: house-writing-style
description: "Use when rewriting, polishing, or auditing natural-language prose in the house style: agent output, docs, release notes, PR and issue text, or when a style violation needs explanation. Code, commands, identifiers, quotes, logs, and structured data stay exact; check the protected-content list before editing."
---

# House Writing Style

## Core Principle

Plain technical English in prose the agent authors. STE-inspired, not formal
ASD-STE100 compliance: the skill adopts controlled-English clarity principles
and adds house-specific spoken-style constraints. Style applies to
natural-language prose. Protected content stays byte-exact.

## When to Use / NOT

- **Use when:** rewriting or polishing prose; drafting docs, release notes, or
 PR and issue text; auditing style; explaining a violation.
- **NOT when:** the user requested a different style for that artifact (the
 user's choice wins); the content is protected (see below).

## Protected content (never rewrite)

Source code, shell commands, code blocks, identifiers, filenames, paths,
URLs, hashes, JSON/YAML/XML payloads, logs, compiler errors, exact quotations,
citations, copied upstream text, user-provided source text when fidelity
matters, and structured machine output.

## Levels

- **L0** kernel only (the AGENTS.md writing-style section): normal chat.
- **L1** kernel + `scripts/style-lint.py`: important generated prose and files.
- **L2** kernel + lint + this skill's review: public docs, release notes,
 important PR and issue text.
- **L3** optional Pi output guard: audit mode first; rewrite only after
 false-positive testing, one pass maximum.

## Hard rules (lint reports ERROR)

Em dashes. Filler intensifiers (`genuinely`, `really`, `truly`, `actually`).
Slop words (`utilize`, `seamlessly`, `effortlessly`, `delve`, `game-changer`,
`supercharge`).
Throat-clearing openers ("it is important to note"). Artificial landing
sentences ("in conclusion"). Decorative separator lines.

## Soft rules (lint reports WARN; judgment applies)

Antithesis; corrective negation; `not only... but also` phrasing; the rule of
three; setup and payoff beats; repetitive parallel sentence syntax; stacked
noun phrases; nominalization.
Unnecessary hedging. Performed enthusiasm. Long sentences. Uniform cadence.
Corporate-register verbs (`leverage`, `underscore`) in vague business use.

## Exceptions (encoded, not negotiable by taste)

- Technical contrast stays: "Use the thread ID, not the comment ID." is good
 writing.
- Parallel structure stays for lists, schemas, and technical sequences.
- Quotes stay exact even when they violate every rule above.
- Domain terminology stays when precision requires it; plain English applies
 to the explanation, never to the terms.

## Workflow

1. Draft in the kernel voice (AGENTS.md, writing-style section).
2. For important prose: run `python3 scripts/style-lint.py <file>`; fix ERRORs,
 judge WARNs.
3. For audits: lint, then apply the semantic checks in
 `references/rules.md`.
4. Never loop: one rewrite pass maximum, re-lint, then send or report.

## Verification

```bash
python3 scripts/style-lint.py --selftest   # fixtures must pass
python3 scripts/style-lint.py              # default docs scope, 0 errors
```

## Red Flags

Rewriting a quotation to satisfy a style rule. Turning a WARN heuristic into a
blocker without false-positive evidence. Claiming ASD-STE100 compliance.
Linting inside code fences or inline code.

## References

- `references/rules.md`
- `references/examples.md`
- `references/exceptions.md`
