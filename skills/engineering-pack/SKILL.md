---
name: engineering-pack
description: "Use when implementing or reviewing code, fixing bugs, testing, finding unused code or dependencies, refactoring, improving performance or security, or choosing APIs, architecture and language practices. Owns implementation and code quality; combine with domain or delivery packs for their parts. Skip procedures for trivial edits."
invocation: entry
---

# Engineering pack

Choose the matching procedure; resolve its paths from its own directory.

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
- Project stack selection or substantial architecture/domain-logic changes:
  assess [Bend](../../knowledge/playbooks/bend-coding-practices/README.md) even when
  not named in the request. Reuse an existing project decision while its
  requirements and constraints hold; skip this assessment for unrelated or
  trivial edits. Compose with the relevant architecture or language procedure.
- Architecture or API contracts:
  [improve-codebase-architecture](../../knowledge/playbooks/improve-codebase-architecture/README.md) or
  [api-and-interface-design](../../knowledge/playbooks/api-and-interface-design/README.md).
- Security/authentication boundaries:
  [security-and-hardening](../../knowledge/playbooks/security-and-hardening/README.md).
- Blocking disposable or bot signups on a product policy list:
  [signup-abuse-response](../../knowledge/playbooks/signup-abuse-response/README.md).
- Unused exports, files, dependencies or duplicate code in JS/TS:
  [fallow](../../knowledge/playbooks/fallow/README.md) when available, alongside
  source and consumer inspection.
- Review a patch or investigate over-engineering:
  [code-review-and-quality](../../knowledge/playbooks/code-review-and-quality/README.md).
- Simplifying working code:
  [code-cleanup](../../knowledge/playbooks/code-cleanup/README.md).
- Language/framework standards: select each materially applicable
  [language or platform](references/languages.md). FastAPI/Flask-style routes to
  Python; framework internals come from that framework's own source or docs.

For planning, design scrutiny, migrations, performance, external-service tests,
bootstrap or other engineering questions, select additional
[topics](references/topics.md) only for distinct active decisions. A named tool
does not automatically justify loading its entire methodology.
