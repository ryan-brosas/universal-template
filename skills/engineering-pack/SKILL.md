---
name: engineering-pack
description: "Use when implementing or reviewing code, debugging failures, designing APIs or architecture, choosing language/framework practices, testing, refactoring, optimizing, or securing software. Git/CI delivery belongs to delivery-pack; visual design belongs to design-pack. Skip procedures for trivial edits."
invocation: entry
---

# Engineering pack

Choose one procedure for the actual problem; do not impose a workflow on trivial
edits. Read only its needed references. Resolve paths and helper commands from
the selected procedure's directory, never from this router.

- Clarify an idea before implementation:
  [brainstorming](../../knowledge/playbooks/brainstorming/README.md).
- Explore a data model or state machine:
  [prototype](../../knowledge/playbooks/prototype/README.md) (shared with design-pack).
- Failure, broken tests or unexpected behavior:
  [debugging-and-error-recovery](../../knowledge/playbooks/debugging-and-error-recovery/README.md).
- Tests and regression coverage:
  [test-generation](../../knowledge/playbooks/test-generation/README.md).
- Green checks without evidence:
  [false-green-gates](../../knowledge/playbooks/false-green-gates/README.md).
- Architecture or API contracts:
  [improve-codebase-architecture](../../knowledge/playbooks/improve-codebase-architecture/README.md) or
  [api-and-interface-design](../../knowledge/playbooks/api-and-interface-design/README.md).
- Security/authentication boundaries:
  [security-and-hardening](../../knowledge/playbooks/security-and-hardening/README.md).
- Simplifying working code:
  [code-cleanup](../../knowledge/playbooks/code-cleanup/README.md).
- Language/framework standards: choose one [language or platform](references/languages.md).
  FastAPI/Flask style routes to Python; framework internals come from that framework's own source or docs.

For planning, design scrutiny, migrations, performance, external-service tests,
bootstrap or other engineering questions, choose one [topic](references/topics.md).
A named tool does not automatically justify loading its entire methodology.
