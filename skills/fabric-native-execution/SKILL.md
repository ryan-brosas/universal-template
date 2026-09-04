---
name: fabric-native-execution
description: "Use when working inside Pi Fabric: core fabric_exec execution first, native providers (memory, state, compact) as helpers, and deliberate escalation to agents/Veda runner or Schema audit/enforce when the task benefits."
invocation: internal
disable-model-invocation: true
---

# Fabric-Native Execution

Core `fabric_exec` is the ordinary execution path. Native providers are
read/write helpers around it. Agents, workflows, the Veda runner, and Schema
modes are deliberate escalations, use them when the task benefits, never as
automatic ceremony.

## Core Principle

Use core `fabric_exec` for ordinary work. Escalate deliberately: `agents.run`
for delegation or parallelism, the Veda runner for frontier-model oracles,
Schema audit for observation, Schema enforce only for intentionally strict
transactional mutation.

## When to Use / NOT

**Use**, any Pi Fabric work: normal code-mode execution; conditional recall
or short-lived coordination state via providers; deliberate delegation or
review escalation.

**NOT**, replacing the project's tracked files with runtime state; running
agents, Veda, or Schema out of habit; `mesh` coordination when one process
suffices.

## Workflow, the layers

1. **Core path (default).** `fabric_exec` with `pi.read`/`pi.edit`/`pi.write`/
 `pi.bash` and tool/MCP composition. `/fabric prewalk` continues execution
 after a mutation boundary when armed. This is normal development.
2. **Native providers (helpers).**
 - `memory.recall` / `memory.expand` (when available): conditional retrieval
 and projection helpers over historical session evidence. Provider output is
 not canonical truth; a recalled code claim is checked against current
 source, and recall is never a default first step.
 - `state.get` / `state.put` / `state.list`, short-lived coordination
 values (active work ID, handoff payloads) that survive across
 `fabric_exec` calls without touching repo dotfiles.
 - `compact.request`, compaction at a safe boundary.
 - Degrade to current source, Git, accessible session history, or an
 explicitly supplied transcript when a provider is missing, and say so. No
 memory write or synchronization step is required after ordinary work.
3. **Agent escalation (deliberate).** Choose the mechanism with
 `skills/execution-router` (its runner-compatibility table applies here:
 native runners are pi/claude/veda; RLM and recursive Fabric require the Pi
 runner) and resolve the backend/model mechanically with
 `skills/model-resolution`.
 `agents.run({ runner: "pi", model })` runs a **native Pi child, which may
 use a different configured provider/model than Main** (cheaper workers,
 stronger reviewers, rate-limit spread; options via `pi --list-models`).
 `agents.run({ runner: "veda", persona, model })` launches the Veda CLI as
 a one-shot headless child for alternate-provider/model oracles (review,
 navigation, hard planning). Veda children have no steering, no persistent
 actors, and no recursive Fabric; select persona/model from the installed
 catalog (`veda personas`, `veda models [backend]`), never from hard-coded
 names. Same-model children are valid when the value is context isolation.
4. **Schema (intentional).** `off`, normal host behavior. `audit`, behavior
 unchanged; records what enforce would block (policy telemetry).
 `enforce`, strict evidence-gated transaction mode: blocks direct
 `pi.edit`/`pi.write`/`pi.bash` and disables Fabric Prewalk; select it deliberately
 for postcondition-critical work. Schema never replaces tests, the
 compiler, IDE semantics, or review.

## Rules

- Evidence over prose: cite the provider result when you rely on it.
- Never write repo files through `state`; it is runtime state, not the
 durable record, tracked files stay authoritative.
- Do not build a persistence layer: one `put` for a value, one `recall` for a
 decision, one `compact.request` per boundary.
- Escalate to agents/Veda/Schema only for a named benefit (parallelism,
 frontier review, transactional guarantee). Do not forbid them globally and
 do not require them by default.
- If a provider is missing or refused, degrade to reading the tracked files
 and say so.

## Red Flags

Writing repo files through `state`; building a persistence or memory-sync layer; treating recalled output as canonical truth; dispatching
agents or Veda as an automatic phase after every change; enabling Schema
enforce (which disables Fabric Prewalk) without an explicit transactional need;
relying on a provider result without citing it.

## Verification

Normal work: the named project checks pass (tests/compiler/lint). Provider
reliance: cite the recalled value or state. Agent/Veda escalation: the child
report is advisory, verify load-bearing findings against source/tests before
acting. Schema enforce: only `committed` postconditions count, and never as a
substitute for behavior verification.


## References

N/A, no reference files; provider and escalation contracts are inline in this skill.
