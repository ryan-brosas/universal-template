---
name: research-pack
description: "Use when investigating source or documentation, finding external facts, navigating indexed source or IDEs, browsing/extracting web or PDF content, consulting Oracle explicitly, or researching mathematics. This pack owns evidence acquisition and may combine with any pack whose decisions depend on that evidence; agent runtime setup remains agent-tooling's boundary."
invocation: entry
---

# Research pack

Use the nearest sufficient evidence. Known local questions stay direct; broad
unresolved codebase questions can use Sourcebot's `ask_codebase` when relevant
indexed coverage helps. The cross-repository source playbook owns applicability,
scope and fallbacks. A session or phase change is not a research trigger.
Figma/Paper-only tasks stay with design-pack and live design evidence; mixed tasks
select research only for the question it owns. Start with the narrowest relevant
procedure and resolve its references and helpers from its own directory.

- Investigate broad codebase questions with Sourcebot's `ask_codebase` when
  indexed coverage is useful, or retrieve external implementations:
  [cross-repo-source](../../knowledge/playbooks/cross-repo-source/README.md).
- Study a reference repository or adapt prior art:
  [reference-driven-development](../../knowledge/playbooks/reference-driven-development/README.md).
- Explicit Oracle consultation:
  [oracle-consult](../../knowledge/playbooks/oracle-consult/README.md).
- Browser inspection/automation:
  [cdp](../../knowledge/playbooks/cdp/README.md).
- PDF extraction:
  [pdf-extract](../../knowledge/playbooks/pdf-extract/README.md).
- Conjecture-driven mathematics and Lean proofs:
  [math-schema](../../knowledge/playbooks/math-schema/README.md).

Select additional [specialists](references/topics.md) only when distinct research
questions require them: search services, financial data, IDE tooling,
document-backed scrutiny, media or source acquisition. Native tool discovery owns
live schemas; these procedures do not guarantee tool availability.
