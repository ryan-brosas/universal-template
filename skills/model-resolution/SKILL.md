---
name: model-resolution
description: "Use when a task or delegated lane needs a concrete model or backend; inspect live availability, choose the smallest sufficient option, probe uncertainty, and escalate only from observed gaps."
invocation: internal
disable-model-invocation: true
---

# Model Resolution

## Core Principle

Start with the task, then inspect current runtime capabilities. Model names,
provider availability, authentication, context limits, and tool support are live
state. No fixed role threshold or tracked preference is universal truth.

## When to Use / NOT

- **Use when:** a task, review, investigation, or delegated lane needs a model
  choice that the current host has not already made.
- **NOT when:** the active model is sufficient and changing lanes adds no value.

## Workflow

1. Identify the task's actual needs: reasoning depth, tools, modalities, context,
   latency, cost, and failure risk. Separate requirements from preferences.
2. Probe current availability through the host's native surfaces, such as
   `pi --list-models`, `veda models`, `agy models`, provider APIs, or exposed
   model inventory tools. Check authentication in the execution environment.
3. Choose the smallest available model that is plausibly sufficient. Use
   `config/model-profiles.yaml` only for portable task needs. If present,
   `config/model-profiles.local.yaml` may break ties after live discovery; it
   remains untracked and is never capability evidence.
4. Verify an uncertain capability with one bounded representative probe before
   assigning load-bearing work.
5. Escalate only when observed output or a capability gap justifies a stronger,
   larger, or different model. Do not retry the same unsuitable lane blindly.

## Fallbacks

Infrastructure failure means choose another currently available candidate or
continue with the active model. Weak output means refine the requirement and
escalate capability. Record the observed gap, not a permanent claim about the
provider.

## Red Flags

- Starting from a model slug and inventing a workflow around it.
- Treating installed as authenticated or advertised context as observed fitness.
- Fixed role-to-context thresholds, global rankings, or tracked runtime status.
- Requiring an optional resolver script before native discovery.

## Verification

The choice is traceable from task requirements to live inventory, bounded probe
when needed, selected model, and any observed reason for escalation.

## References

- `../execution-router/SKILL.md`, when execution shape must be chosen first.
- `../veda-lane/SKILL.md`, native Veda lane execution.
- `../../config/model-profiles.yaml`, portable task-needs profiles.
- `../../scripts/runtime-capabilities.py`, optional aggregate diagnostic.
