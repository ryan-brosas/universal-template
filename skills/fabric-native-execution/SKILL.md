---
name: fabric-native-execution
description: Use when executing Pi Fabric work that can lean on native providers (memory, state, compact) inside fabric_exec, or when a workflow needs durable session state or cross-session recall.
disable-model-invocation: true
---

# Fabric-Native Execution

Prefer Pi Fabric's native providers over hand-rolled files and shell caches. The Schema loop stays the mutation gate; these providers are read/write helpers around it, never a replacement for `schema.hypothesize → verify → commit` on repo files.

## Core Principle

Native providers are read/write helpers around the Schema loop — never a replacement for `schema.hypothesize → verify → commit` on repo files.

## When to Use / NOT

**Use** — executing Pi Fabric work that can lean on native providers (memory, state, compact) inside `fabric_exec`; workflows that need durable session state or cross-session recall.

**NOT** — repo file mutations (the Schema loop is the gate); multi-actor coordination via `mesh`; subagent dispatch via `agents.run`.

## Workflow

1. `memory.recall` / `memory.expand` before re-deriving past decisions ("what did we decide about X").
2. `state.put` short-lived coordination values (active work ID, current station, handoff payloads) so they survive across `fabric_exec` calls without touching repo dotfiles.
3. `compact.request` at a safe boundary between stations; keep the handoff payload in `state` or the station ledger, not only in memory.
4. If a provider is missing or refused, degrade to reading the tracked files and say so.

## Providers

- `memory.recall` / `memory.expand` — search past sessions and durable decisions for evidence before re-deriving them. Use for cross-session recall ("what did we decide about X").
- `state.get` / `state.put` / `state.list` — versioned shared state keyed by prefix. Highly valuable for short-lived coordination values (active work ID, current station, handoff payloads between `/ship` stations, verification cache). Use this to survive across `fabric_exec` calls without repeatedly touching repo dotfiles.
- `compact.request` — ask the host to compact context at a safe boundary (used by `/ship` between stations). Keep the handoff payload in `state` or the station ledger, not only in memory.

## Rules

- Evidence over prose: cite the provider result (value, recall hit, event) when you rely on it.
- Never write repo files through `state`; it is runtime state, not the durable record. The work ledger (`.pi/work/<slug>/.progress.md`) stays authoritative for history.
- Do not use `mesh` (multi-actor coordination is overkill for a local template) and do not dispatch subagents (`agents.run`).
- If a provider is missing or refused, degrade to reading the tracked files and say so.
- Do not build a persistence layer: one `put` for a value, one `recall` for a decision, one `compact.request` per station boundary.

## Red Flags

Writing repo files through `state`; building a persistence layer (more than one `put` for a value, one `recall` for a decision, one `compact.request` per station boundary); using `mesh` or dispatching subagents (`agents.run`); relying on a provider result without citing it.

## Verification

Cite the provider result (value, recall hit, event) when you rely on it. When degrading to reading the tracked files because a provider is missing or refused, say so explicitly.

## Skill Result Contract

```
<skill_result>
  <skill>fabric-native-execution</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>…</evidence>
  <artifacts>…</artifacts>
  <risks>…</risks>
</skill_result>
```

## References

N/A — no reference files; provider contracts and rules are inline in this skill.
