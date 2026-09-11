---
name: coding-best-practices
description: "Use when the user asks for engineering standards, coding best practices, quality guidance, or the applicable quality procedure. Route to the narrowest language/framework leaf or gate; not for ordinary implementation."
invocation: entry
---

# Coding best-practices router

This is a selection map, not a general implementation phase. Project source,
instructions, tests, and runtime behavior remain authoritative.

## Route narrowly

1. A named language or framework routes to an existing matching
   `*-coding-practices` leaf. When a framework has no practices leaf of its own
   (FastAPI, Flask), route style questions to its underlying language leaf
   (`python-coding-practices`) and route to `../foundation-pack/SKILL.md` only
   when the request needs that project's internals rather than general style.
   TypeScript domain modeling may additionally need
   `typescript-coding-standards`; do not load both by default.
2. Scope control, maintainability, verification discipline, or design judgment
   routes to `../code-discipline/SKILL.md`.
3. Test design routes to `../test-generation/SKILL.md`,
   `../test-driven-development/SKILL.md`, or
   `../testing-anti-patterns/SKILL.md` according to the request.
4. Security review routes to `../security-and-hardening/SKILL.md`. Turning a
   stable exact practice into automation routes to `../practices-to-ci/SKILL.md`.
5. Completion evidence routes to `../agent-code-quality-gate/SKILL.md`; PR
   delivery routes to `../push-pr/SKILL.md`. Neither is implied by a general
   standards question.
6. Skill authoring routes to `../writing-skills/SKILL.md`; template-repository
   maintenance also loads `../template-maintenance/SKILL.md`.

If the topic is broader or ambiguous, open
`references/topic-index.md`, choose one row, and load only its cited leaf or
focused reference. The index covers naming and formatting, documentation,
error handling, Git collaboration, AI-assisted code, performance, and security.
Do not paste the entire guide into the task or restate DRY/KISS/YAGNI as rigid
rules.

## Verify and stop

A routing answer names the selected owner and why close alternatives do not own
the request. Implementation work uses that project's real checks; recurring
objective invariants may earn a maintained CI gate when its benefit exceeds
maintenance and false-positive cost. Stop when the question is answered or the
selected gate has produced the evidence actually requested.
