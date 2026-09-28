# Author a playbook or pack

Follow `knowledge/playbooks/writing-skills/README.md`. Prefer a specialist
playbook linked from an existing pack; a new visible pack needs evidence that
existing boundaries cannot route the task clearly.

## Specialist playbook (default)

Create `knowledge/playbooks/<name>/README.md`:

```markdown
---
title: <kebab-case-name>
summary: "Use when <specific task or failure>; supplies <missing capability>."
kind: playbook
---

# <Readable title>

State the useful decision, shortcut or non-obvious contract. Omit generic advice
already supplied by the project or model. Preserve valid implementation choices.

## Boundaries

Explain consequential scope, safety or protocol constraints, when needed.

## Verification

Name evidence of the actual task outcome, not compliance with this document.

## References

- `references/<topic>.md`: when this additional detail helps.
```

Keep assets, references and helpers beside the playbook; resolve paths from that
directory. Link the playbook from exactly one pack's cold index. Other pack indexes
may cross-link it; label those entries with the owning pack, and do not copy its
instructions. Preserve attribution and license metadata. Do not add `name`,
`description`, invocation fields or `SKILL.md` to the playbook: those can turn
ordinary content back into discovered skills.

## Visible router (only when justified)

Create `skills/<name>-pack/SKILL.md`:

```markdown
---
name: <name>-pack
description: "Use when <ordinary user intent, artifact or failure symptom>; owns <specific decisions>. Combine with <relevant owners> for distinct work; not for <likely near miss>."
invocation: entry
---

# <Name> pack

Choose the matching procedure; resolve its paths from its own directory.

- <Specific intent>: [procedure](../../knowledge/playbooks/<name>/README.md).
```

A task may load multiple packs; keep this router scoped to the decisions it owns.
Canonical playbook ownership remains singular even when another pack cross-links
it. Keep routers small; large branches use a plain Markdown topic index. Never
load a whole index recursively. No global workflow, installer, generated catalog
or mandatory evaluation framework is required.

Verify paths, coverage, host discovery, relevant helper callers and routing.
For material routing changes, compare unnamed task requests before and after,
including a near miss and compound task; inspect actual reads and report
unmeasured behavior honestly. Read source evidence directly when a procedure needs it; do not create a
permanent source summary.
