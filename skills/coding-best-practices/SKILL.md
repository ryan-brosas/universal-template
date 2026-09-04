---
name: coding-best-practices
description: "Use when the user explicitly asks for engineering standards, coding best practices, quality guidance, or help selecting a quality procedure or leaf skill, routes the topic to the right leaf or mechanical gate instead of restating rules."
invocation: entry
---

# Coding Best Practices, topic router

## Core Principle

General coding guidance is a **map**, not a monolith. Route each topic to one leaf skill or one mechanical gate; steer outcomes with checks, not walls of prose.

## When to Use / NOT

- **Use when:** the user explicitly asks for best practices, standards, or quality guidance ("what are best practices for X?"), onboarding someone to how this catalog expects work to flow, or choosing which quality skill to load next.
- **Use when:** the question spans naming, docs, Git, testing, security, or AI-generated code and you need the right pointer fast.
- **NOT when:** a normal implementation task starts, the ordinary loop (inspect, implement, verify) needs no router; load this only when standards guidance is the actual request.
- **NOT when:** the task is TypeScript-only, load `typescript-coding-practices` (style/modules) and `typescript-coding-standards` (domain modeling) instead of this router alone.
- **NOT when:** declaring work complete, load `agent-code-quality-gate` and the
  project's verification commands from its `AGENTS.md` or contributor docs.
- **NOT when:** opening or updating a PR, load `push-pr`.
- **NOT when:** deep Git conventions from community guides, load `awesome-guidelines`.
- **NOT when:** authoring a new skill, load `writing-skills`.

## Workflow

1. **Classify the topic** using `references/topic-index.md` (naming, docs, errors, Git, AI, performance, principles).
2. **Load the leaf** cited on that row, never paste the whole guide inline.
3. **Implement** under `code-discipline` (scope, verification, one source of truth).
4. **Test** under `quality-gate-methodology` / `test-driven-development` / `testing-anti-patterns` as appropriate.
5. **Review** under `code-review-and-quality` before merge when human or agent review is in scope.
6. **Enforce** anything mechanical via `practices-to-ci` and the project CI gate, if it can be a check, do not leave it as a prompt.
7. **Ship** via `push-pr` when the branch is ready.
8. Stop when the topic is answered by the loaded leaf and any applicable gate has exit 0 evidence.

## Topic → leaf (quick map)

| Topic | Load first | Mechanical gate |
|---|---|---|
| Scope, verification, design taste | `code-discipline` | project CI + `agent-code-quality-gate` |
| Naming, formatting, readability | `references/naming-and-formatting.md` | linter/formatter + `typescript-coding-practices` / `javascript-coding-practices` when stack-specific |
| README, docstrings, comments | `references/documentation-and-readme.md` | `repo-hygiene` (catalog) |
| Errors, resilience | `references/error-handling-and-resilience.md` | behavior tests |
| Git, branches, PRs | `references/git-and-collaboration.md` | `push-pr`, conventional commits |
| AI-generated code | `references/ai-assisted-coding.md` | `agent-code-quality-gate` |
| Performance / data efficiency | `references/performance-and-data-efficiency.md` | profile-first; benchmark in CI when stable |
| Security | `security-and-hardening` | secret scan, dependency audit |
| Turn practice into CI | `practices-to-ci` | the project's PR quality workflow |

## Red Flags

- **HARD-GATE:** Prompting for something mechanically enforceable instead of adding a CI check (`practices-to-ci`).
- Loading this router and then ignoring the cited leaf, the router has no rules of its own beyond routing.
- Treating DRY/KISS/YAGNI/SOLID as behavioral walls; use them as decision hints, then verify with project gates.
- A "best practices" answer with no named skill, no gate command, and no evidence.

## Verification

- The chosen topic row from `references/topic-index.md` names a leaf skill or reference file you opened.
- For implementation work: `agent-code-quality-gate` five checks recorded before claiming done.
- For template catalog edits: inspect local skill metadata and run the relevant hard-contract checks documented by that repository.


## References

- `references/topic-index.md`, full topic-to-skill and gate table.
- `references/naming-and-formatting.md`, names, conventions, comments, whitespace.
- `references/documentation-and-readme.md`, README, docstrings, why-not-what comments.
- `references/error-handling-and-resilience.md`, errors at boundaries, tests over try/except alone.
- `references/git-and-collaboration.md`, Git, branches, commits, PRs.
- `references/ai-assisted-coding.md`, reviewing generated code, context files, no blind trust.
- `references/performance-and-data-efficiency.md`, profile first, vectorize/chunk when measured.
- `awesome-guidelines`, archived cold library; its `references/` capsules feed the `*-coding-practices` leaves (no new ingestion).
- `deep-module-design`, structural quality review when the topic is module boundaries or interface complexity.
