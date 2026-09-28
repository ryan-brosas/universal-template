# Author a playbook or pack

Follow [writing-skills](../knowledge/playbooks/writing-skills/README.md). Prefer a
specialist linked from an existing pack; a new visible pack needs evidence that
existing boundaries cannot route the task clearly. Creation paths below are
relative to the repository root.

## Specialist playbook (default)

Create `knowledge/playbooks/<name>/README.md`:

```markdown
---
title: <kebab-case-name>
summary: "Use when <specific task or failure>; supplies <missing capability>."
kind: playbook
---

# <Readable title>

Explain the task-specific decision and the evidence needed to make it. Omit
generic advice already supplied by the project or model. Preserve valid approaches.

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

Review paths, coverage, host discovery and callers directly. For material routing
changes, observe whether ordinary work leads the agent to read and use the right
guidance; a prompted skill choice does not establish that. Do not add scripted
routing or instruction-validation machinery. Report unobserved behavior honestly.
Read source evidence when needed instead of creating a permanent source summary.
