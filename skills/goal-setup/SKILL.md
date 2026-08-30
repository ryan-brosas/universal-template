---
name: goal-setup
description: "Use when significant, ambiguous, high-risk, or multi-session work needs a durable execution contract with explicit scope, completion criteria, key decisions, and verification."
---

# Goal Setup

## Core Principle

Some work needs a durable coordination contract, a migration that spans days, a risky architecture change, cross-agent or cross-team execution. Goal setup captures exactly that contract in ONE artifact; it never manufactures planning ceremony for ordinary work.

Separation of jobs: **brainstorming** decides what to do · **goal-setup** defines what counts as done · implementation does it.

## When to Use / NOT

- **Use when:** multi-day migration; significant architecture change; major feature; risky production change; multi-agent/cross-team coordination; an explicit user request for an implementation plan.
- **NOT when:** typo fixes, small bugs, isolated features, obvious refactors, dependency updates. Duration, ambiguity, risk, coordination, or irreversible decisions earn this skill, nothing else does. Ordinary feature work goes straight to implementation.

## Workflow

1. **Check for an existing coordination system.** If the project uses GitHub Issues/milestones, Linear, Jira, or similar, anchor the goal there and keep the local artifact thin, do not duplicate project management into Markdown.
2. **Choose the artifact location by repository convention**, `docs/plans/<goal>.md` by default; adapt to `docs/adr/`, `design/`, or whatever the project already uses. Never force a tool-specific directory onto a project with its own organization.
3. **Write ONE artifact** (create the directory only when it does not exist):

````markdown
# Goal: <name>

## Outcome
<the end state, one paragraph>

## Scope
<what this goal covers>

## Non-goals
<explicitly out of scope — prevents drift>

## Accepted facts / constraints
<decisions, constraints, and traps that are expensive to reconstruct>

## Done when
<concrete, verifiable completion criteria — the gates that prove it>

## Important decisions
<chosen direction + rejected alternatives, appended as made>

## Execution outline
<cohort/phase list — coarse, not a task tracker>

## Verification
<how each phase and the whole goal are verified>

## Open risks
<known unknowns and mitigations>
````

4. **During execution:** update only meaningful state, decisions made, risks closed, criteria met. Never turn the goal file into a Git/state cache (branch, dirty state, last commit are recoverable from Git).
5. **Close:** when the Done-when criteria are verifiably met, mark the goal closed (one line + evidence). Exceptional reusable lessons → `leverage-capture`.

Only split into multiple files when real scale demands it (rare; each split must name its seam).

## Red Flags

- Creating a six-file planning package by default. HARD-GATE, one artifact.
- Goal artifacts for ordinary single-session work.
- Duplicating an existing tracker (Issues/Linear/Jira) into Markdown.
- Goal file as Git-state cache (branch/commit/dirty-state entries).
- Done-when criteria that no gate can verify.

## Verification

The goal artifact exists at the repository-conventional location; every Done-when criterion maps to a runnable verification or explicit manual check; the coordination system (if any) is referenced, not duplicated. On resume: read the goal artifact + Git state, never a stale global state file.

## References

- `../brainstorming/SKILL.md`, the direction decision that precedes this
- `../leverage-capture/SKILL.md`, post-goal knowledge classification
- `~/.agents/templates/roadmap.md`, only when a multi-goal product roadmap is explicitly requested
