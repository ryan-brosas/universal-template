---
name: goal-setup
description: "Use when a roughly four-day-or-longer effort needs a compact post-code work record for recovery, handoff, or an explicit user, project, or external coordination requirement."
invocation: entry
---

# Goal Setup

## Core Principle

Most implementation should proceed from source, tests, examples, and the conversation. `goal-setup` exists only when a genuinely long-running effort needs durable recovery or handoff state that those surfaces cannot cheaply provide. It records verified work after it happens; it does not manufacture an implementation specification before coding.

Separation of jobs: **brainstorming** decides what to do · implementation proves it in code and tests · **goal-setup** preserves only qualified long-run post-code state.

## When to Use / NOT

- **Use when:** work is expected to run for roughly four days or longer **and** needs meaningful recovery or handoff beyond source, Git, the project tracker, and project-scoped session evidence; or the user, repository/project policy, an external tracker, an ADR process, a compliance rule, or a cross-team coordinator explicitly requires a durable record.
- **NOT when:** the user merely asks for a plan; the work is ambiguous, high-risk, or multi-session; a feature, migration, refactor, or production change is still manageable from source and normal project tracking; or no verified pass exists yet. Those conditions call for conversation, direct implementation, or the existing coordinator—not a repository plan file.

## Workflow

1. **Start from current truth.** Inspect the relevant source, tests, examples, project tracker, and local instructions. Decide and implement in conversation; do not create a local artifact before the first verified pass unless the user, repository/project policy, or an external coordinator requires one.
2. **Prove the record is earned.** Confirm the expected duration/recovery or handoff need, and check whether an existing tracker already owns the coordination. Keep the tracker authoritative; do not duplicate it into Markdown.
3. **Choose the native location.** Use the repository’s established work-record or coordination location. If none exists, ask before inventing a directory; do not default to `docs/plans/`.
4. **Write one compact post-code record** after a verified pass:

````markdown
# Work record: <name>

## Verified pass
<what changed or was proven>

## Source and evidence
<paths, tests, runtime evidence, and source pin when material>

## Decision and counter-evidence
<what was chosen and why meaningful alternatives were rejected>

## Omitted or unresolved
<what was intentionally not done or still needs evidence>

## Next target
<only when the run continues>
````

5. **Maintain only expensive-to-reconstruct state.** Append verified outcomes, meaningful decisions, and the next target. Never copy source facts, pseudo-code, task decomposition, Git state, or tracker contents into the record.
6. **Close or remove.** When the work no longer needs durable recovery or handoff, mark the outcome with its evidence. Remove an unneeded local record when project policy permits; reusable lessons go through `leverage-capture`.

Only split records when a real handoff boundary demands it; each split must name that boundary.

## Red Flags

- Creating a plan, design document, or work record merely because the user asked to plan. HARD-GATE.
- Creating a record before a verified pass without an explicit user, project, or external coordination requirement.
- Treating ambiguity, risk, or multiple sessions as sufficient reason for an artifact.
- Duplicating an existing tracker into Markdown.
- Work record as a Git-state cache, source mirror, pseudo-code specification, or task tracker.
- Recording claims that lack source, test, runtime, or explicit manual-check evidence.

## Verification

The record, if created, has a qualified long-run/handoff or external-coordination justification, lives at the repository-conventional location, and contains only verified post-code state. Every evidence claim points to a runnable verification or explicit manual check. On resume, read current source, Git state, and the authoritative tracker first; use the record only for the irrecoverable context it preserves.

## References

- `../brainstorming/SKILL.md`, conversational direction decision
- `../leverage-capture/SKILL.md`, post-work knowledge classification
- `../../templates/roadmap.md`, only when a multi-goal product roadmap is explicitly requested
