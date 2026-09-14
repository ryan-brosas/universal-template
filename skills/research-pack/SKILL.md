---
name: research-pack
description: "Use when investigating source or documentation, finding external facts, navigating indexed source or IDEs, browsing/extracting web or PDF content, consulting Oracle explicitly, or researching mathematics. This pack owns evidence acquisition and may combine with any pack whose decisions depend on that evidence; agent runtime setup remains agent-tooling's boundary."
invocation: entry
---

# Research pack

At the start of every repository work session, use Sourcebot's `ask_codebase` as
the default context bootstrap when Sourcebot is available and relevant indexed
coverage exists; the cross-repository source playbook owns scope and fallbacks.
After that kickoff, use the nearest sufficient evidence: known source paths can
be read directly, and bounded Sourcebot follow-ups support planning,
implementation, verification and review when the decision surface changes. Start
with the narrowest relevant procedure and add another only for a distinct research
question. Resolve each procedure's references and helpers from its own directory.

- Investigate indexed code across all four phases (including an indexed current
  repository) with Sourcebot's `ask_codebase`, or retrieve external
  implementations:
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
