---
title: documentation-and-adrs
summary: Use when writing technical documentation, ADRs, API docs or project READMEs; choose the audience and document type, preserve project conventions, and verify claims against current behavior.
kind: playbook
---

# Documentation and ADRs

Document what a reader needs to understand, use or maintain the system. Reuse
existing documents and conventions rather than creating a second inventory.
Ephemeral discussion belongs in the conversation unless a durable record serves
a concrete reader or recovery need.

## Choose the document

- **README:** what the project is, who it serves and how to get started.
- **Architecture:** system boundaries, responsibilities and consequential flows.
- **Guide or API reference:** completing a task or using a contract.
- **Runbook:** diagnosing and operating a system, with safe commands and recovery.
- **ADR:** why a consequential decision was made and when it should be revisited.

These are responsibilities, not a mandatory directory tree. Keep the project's
existing locations and formats unless changing them is part of the task.

## Record a decision when the rationale matters

An ADR is useful when genuine alternatives had material trade-offs and future
maintainers would otherwise lose the rationale. Do not write one for every
implementation choice or fill a template merely because it exists.

A structured starting point, when the project has no preferred format:

```markdown
# ADR-NNN: Title

**Status:** proposed | accepted | deprecated | superseded by ADR-XXX
**Date:** YYYY-MM-DD
**Context:** Situation, constraints and decision drivers.
**Decision:** Chosen direction and scope.
**Consequences:** Benefits, costs and remaining risks.
**Alternatives considered:** Credible options and why they were not chosen.
```

A small decision can use prose instead of headings, but retain enough context,
consequences and alternatives for a reader to judge whether it still applies.
Do not mark a proposed decision accepted without agreement.

## Write and maintain

1. Identify the audience, task and authoritative source. Read the relevant code,
   current interface or operating evidence before documenting behavior.
2. Explain the non-obvious parts. Link existing reference material rather than
   copying facts that will drift. Keep commands, identifiers and quotations exact.
3. Update affected documentation with the behavior change. Preserve useful
   rationale when retiring obsolete instructions.
4. Verify the changed claims and examples using the relevant existing checks or
   safe execution path. Distinguish tested instructions from untested examples;
   do not install, reset or publish merely to exercise a document.

Age alone does not make a document wrong. Correct or remove content because its
claims are obsolete, misleading or no longer useful, not because it has gone six
months without edits.

## Review the result

Can the intended reader complete the task or understand the decision? Are links,
commands and claims current? Is each fact maintained by one owner? Report
unverified examples and environmental requirements rather than implying a fresh
installation or complete workflow was tested when it was not.
