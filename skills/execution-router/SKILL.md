---
name: execution-router
description: "Use when deciding HOW a task should be executed before starting it: Main directly, an isolated child, bounded parallel workers, an alternate-model oracle, recursive decomposition (RLM), or a persistent actor, plus what each participant may write."
---

# Execution Router

## Core Principle

Three decisions, kept separate: the **evidence router** decides WHERE evidence
comes from (evidence sources only, never model selection), the **execution
router** (this skill) decides HOW work is executed, and **model-resolution**
decides WHICH backend/model runs each chosen role. Choose the mechanism first;
model selection is then mostly mechanical (`skills/model-resolution`).

## When to Use / NOT: when is an execution mechanism worth choosing?

The six decisions below are the dispatch questions; any task that needs a
mechanism decision instead of doing the work directly routes here.

Answer each independently, a task can combine answers:

1. **Can Main handle it directly?** Default. Escalating a small task is the
 violation, not the answer.
2. **Does part of it need isolated context?** → child on that part only (one
 subsystem, one reference repo, one bounded question). A same-model child
 with fresh context is valid: judge children on context/responsibility
 distinctness, not on model identity.
3. **Are there independent workstreams?** → parallel workers, but only when
 each owns meaningfully different evidence or slices, no redundant clones
 without an independent-sampling reason. Bound concurrency; isolate writes
 (git worktrees or non-overlapping file sets).
4. **Is context still the binding constraint after partitioning?** → recursive
 decomposition (RLM) to shrink the problem before spending model effort.
 Partition with Fovea first; RLM requires the Pi runner.
5. **Does a responsibility outlive this task?** → persistent Actor with its
 own trigger, outside the one-shot path.
6. **Does a step need different or stronger reasoning?** → attribute the
 capability requirement (a role) and let model-resolution find the lane.
 Capability is a requirement, not an escalation level.

## Workflow

Pick the mechanism first, then the runner; verify the runner against the
installed Fabric version.

## Runner compatibility (verify per installed Fabric version)

| Mechanism | pi | claude | veda |
|---|---|---|---|
| Recursive Fabric / RLM | yes | no | no |
| Steering | yes | yes | no |
| Persistent actor | yes | yes | no (one-shot) |
| fabric_exec / mesh | yes | no | no |
| Worktree isolation | yes | yes | yes |

Native Fabric runners are `pi`, `claude`, and `veda`. Claude children get no
recursive Fabric capabilities; Veda children are one-shot headless. Probe an
untrusted lane with a one-shot run before trusting it with real work.

## Permission defaults

- Investigator / reviewer / oracle roles: **read-only**.
- Worker roles: **write only on their declared scope**; parallel workers run
 in isolated worktrees or non-overlapping file sets.
- Actors: the minimum tools their trigger needs; long-lived, so audit their logs.

## Review routing (risk-proportional, do not double-review by default)

| Change | Verification surface |
|---|---|
| Tiny local change | tests / lint only |
| Cross-file structural refactor | Fovea impact + tests |
| Type-sensitive refactor | Steroid semantic check + tests |
| High-risk architecture | independent review + semantic/mechanical verification |
| Frontend visual change | rendered/runtime verification + tests/build (model critique is not rendered evidence) |

## Red Flags

- Building a multi-provider topology for a task one Main pass handles. HARD-GATE.
- Rejecting a same-model child for lacking a different model.
- Identical parallel reviewers without an independent-sampling reason.
- Choosing a model before choosing the mechanism.
- Skipping the evidence router: effort spent on the wrong question is waste.

## Verification

Record the mechanism, role, capability requirements, and permission scope; if
no escalation happened, record that, it is a valid outcome. Model resolution
then proceeds mechanically (`skills/model-resolution`).

## References

- `../model-resolution/SKILL.md`, mechanical backend/model resolution for the chosen role
- `../evidence-router/SKILL.md`, upstream: where evidence comes from
- `../fabric-native-execution/SKILL.md`, execution mechanics (core path, native children, Veda runner, Schema modes)
- `../veda-lane/SKILL.md`, executing through Veda once Veda is chosen
