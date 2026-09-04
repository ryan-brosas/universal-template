---
name: execution-router
description: "Use when Main alone is insufficient and child, parallel, RLM, actor, or alternate-model execution is already justified — cold escalation reference."
invocation: internal
disable-model-invocation: true
---

# Execution escalation reference

Default: Main handles the task directly.

Escalate only when the task already needs it:

| Mechanism | When |
|---|---|
| Child | One bounded subsystem, reference repo, or question needs isolated context |
| Parallel workers | Independent slices with isolated writes (worktrees or non-overlapping files) |
| RLM | Context still binding after partition (Pi Fabric runner) |
| Actor | Persistent responsibility outside a one-shot task |
| Alternate model | Reasoning capability is the gap (`model-resolution`) |

Hard constraints: investigator/reviewer roles read-only; workers write only
declared scope; parallel workers do not share writable paths.

Mechanics: `fabric-native-execution`, `model-resolution`, `veda-lane`.
Evidence sourcing stays separate (`evidence-router`).
