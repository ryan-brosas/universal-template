---
name: engineering-pack
description: "Use when implementing or reviewing code, debugging failures, designing APIs or architecture, choosing language/framework practices, testing, refactoring, optimizing, or securing software. This pack owns implementation and code-quality decisions; combine it with relevant domain or delivery packs. Skip procedures for trivial edits."
invocation: entry
---

# Engineering pack

Start with the narrowest procedure for the active engineering problem and add
another only for a distinct engineering subproblem; do not impose a workflow on
trivial edits. Read only the references each needs. Resolve paths and helper
commands from each selected procedure's directory, never from this router.

- Clarify an idea before implementation:
  [brainstorming](../../knowledge/playbooks/brainstorming/README.md).
- Explore a data model or state machine:
  [prototype](../../knowledge/playbooks/prototype/README.md) (shared with design-pack).
- Failure, broken tests or unexpected behavior:
  [debugging-and-error-recovery](../../knowledge/playbooks/debugging-and-error-recovery/README.md).
- Installing, updating, hardening, or recovering a supervised local service:
  [local-service-durability](../../knowledge/playbooks/local-service-durability/README.md).
- Tests and regression coverage:
  [test-generation](../../knowledge/playbooks/test-generation/README.md).
- A host/harness signal on the wrong surface or in the wrong position (durable
  notification vs inline status, badge vs transcript annotation):
  [authoritative-signal-surfacing](../../knowledge/playbooks/authoritative-signal-surfacing/README.md).
- Green checks without evidence:
  [false-green-gates](../../knowledge/playbooks/false-green-gates/README.md).
- Architecture or API contracts:
  [improve-codebase-architecture](../../knowledge/playbooks/improve-codebase-architecture/README.md) or
  [api-and-interface-design](../../knowledge/playbooks/api-and-interface-design/README.md).
- Security/authentication boundaries:
  [security-and-hardening](../../knowledge/playbooks/security-and-hardening/README.md).
- Simplifying working code:
  [code-cleanup](../../knowledge/playbooks/code-cleanup/README.md).
- Language/framework standards: select each materially applicable
  [language or platform](references/languages.md). FastAPI/Flask style routes to
  Python; framework internals come from that framework's own source or docs.

For planning, design scrutiny, migrations, performance, external-service tests,
bootstrap or other engineering questions, select additional
[topics](references/topics.md) only for distinct active decisions. A named tool
does not automatically justify loading its entire methodology.
