# Essential: Guiding Small Models — Ground Truth Beats Capacity

Source: Discord conversation with Tom, 2026-08-21. The first pillar of the
operating philosophy. Treat as an essential.

## 1. The Core Heuristic

> *"A small model lacks knowledge, not capacity. Give it ground truth to work from."*

Small models fail from missing knowledge, not missing intelligence. The fix is
not a longer prompt — it is putting the exact ground truth (code, tests, typed
examples, a proven procedure) into context where the model can copy it. This
is an observed working pattern, not a proven equivalence: treat it as a
testable bet per task.

### What ground truth looks like

- **The code itself** — the nearest existing implementation of what you want.
- **Typed examples** — a concrete input → expected output pair beats a prose spec.
- **A verified skill** — a procedure with a named probe that removes re-derivation.
- **Runtime feedback** — the actual error, exit code, or diff, not a description of it.

### What it does not look like

- Long behavioral rule lists ("always be careful", "never invent APIs").
- Prose specifications describing code that does not exist yet.
- Frozen summaries standing in for the current source.

## 2. The Rules

1. **Code is ground truth, not specs.** When code and prose disagree, the code
   wins. Docs are derived from working code, not the other way around.
2. **The reusable unit is the skill.** Distill repeated procedures into a short
   skill with a verification probe; do not re-explain them in every session.
3. **Discovery beats telling.** Give the model the tools and pointers to find
   the answer (code graph, grep, IDE) rather than pre-digesting everything.
4. **Feed errors back, not warnings.** A failing gate's output is worth more
   than a paragraph of instructions.

## 3. Where the mechanics live now

How skills are authored, how prior art is grounded, and how execution happens
are documented in their own surfaces (`codebase-driven-development`,
`writing-skills`, `fabric-native-execution`) — not here. This file keeps only
the heuristic.
