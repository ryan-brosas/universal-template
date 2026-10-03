---
title: grill-with-docs
summary: Use when a plan must be checked against the project's glossary, ADRs and code; adds documentary evidence to engineering's proposal-scrutiny procedure.
kind: playbook
---

# Stress-test a plan against project evidence

Use [grill-me](../grill-me/README.md) for the interview and stop rule. This
procedure owns the documentary part, not a second general grilling workflow.
It is read-only unless the task includes documentation changes; runtime
permissions and project instructions still apply. No particular harness or
Schema mode is a prerequisite for discussing a plan.

## Ground the questions

- Locate the project's existing glossary and decision records. If it uses a
  `CONTEXT-MAP.md`, follow it to the relevant context; do not assume every project
  uses these filenames or create them merely because they are absent.
- Check disputed claims against current code and documents before asking the
  user. Separate an obsolete document, a code defect and a deliberate change of
  direction rather than assuming one source always wins.
- Surface conflicting or overloaded domain terms with the existing definition
  and a concrete consequence. Offer a recommendation, but do not invent a
  canonical term or silently replace the project's vocabulary.
- Use relevant scenarios to expose boundaries and trade-offs. Stop when the
  consequential decisions are settled or blocked; reviewing every branch of a
  design tree is not an acceptance requirement.

## Record only what the task needs

For a discussion-only request, return resolved terms, strengthened decisions and
open questions in the conversation. If documentation updates are authorized,
reuse the project's existing files and formats. Keep a glossary focused on domain
language rather than implementation plans or session notes.

Offer an ADR when the choice is consequential, its rationale would otherwise be
lost, and genuine alternatives were considered. Follow
[documentation-and-adrs](../documentation-and-adrs/README.md); do not create a
parallel decision log.

## Optional formats

- [CONTEXT-FORMAT.md](CONTEXT-FORMAT.md): a glossary format when the project has
  chosen this convention, not a required repository structure.
- [ADR-FORMAT.md](ADR-FORMAT.md): a minimal note for an authorized small decision
  when the project has no conflicting ADR convention.
