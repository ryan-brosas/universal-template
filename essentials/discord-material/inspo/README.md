# Inspo Adoption — carry the playbook into every build

This directory is the **adoption layer**: pointers that let any project bootstrapped under
workflow-lifecycle start from this material instead of empty context. It is the
"we don't start from zero" wiring for the two methodology skills.

## What's adopted

- `raw/block-001 … block-005` — verbatim Discord thread source (`~/.agents/skills/leverage-playbook/references/*` + `test-generation/references/*` cite these)
- `patterns/` — the 5 OpenViking peer memories backing them

## How a new project consumes it

1. `workflow-lifecycle` /init runs.
2. During /init detection, the agent loads the two playbook skills' `references/` (they
   _are_ the source) and drops context from the raw blocks into the project's AGENTS.md
   collapsible or `.pi/project.md` "Operating principles" section.
3. The project's gates follow `test-generation/references/mechanical-gates.md + cohort-discipline.md` — every rule that can be a gate is a gate, not prose.

## Rules for adopters

- Always cite the verbatim block (`block-00X`) — never paraphrase the Discord source.
- The raw/ + patterns/ + skills/ stay the single source; the project copies only引用 excerpts with a source marker.
- Don't re-register removed servers or scrape .pyc here; keep this pure source material.

## Change log

- 2026-08-26: initial adoption — 5 verbatim blocks + 5 peer patterns → `leverage-playbook` + `test-generation` skills → registered in `pack-delivery`.