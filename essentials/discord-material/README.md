# 📜 Discord Material — verbatim source for the workflow

> **Source:** OpenViking `viking://user/default/peers/hermes/memories/` (patterns,
> cases, events — attributed to sender + date) and
> `viking://user/default/sessions/*/history/archive_001/messages.jsonl`
> (verbatim conversation archives).
> **Store on disk:** `/mnt/hdd/openviking/data/viking/default/user/default/`
>
> This is the **exact, unedited Discord conversation material** you asked to make
> our operating baseline. The `raw/` blocks are byte-verbatim copies of the pasted
> threads (only a `<!-- source -->` marker added). The `patterns/` folder holds the
> OpenViking-distilled pattern memories that cite the same threads.
>
> **Rule:** when the essentials describe a principle, prefer quoting these threads
> verbatim instead of paraphrasing — that is the whole point of keeping them here.

## Thread map — what each block contains

| Block | Date | People | Topic → which essential it feeds |
|---|---|---|---|
| `raw/block-001` | 8/21/26 | Tom, Rykuuun [OAI] | **Code is ground truth, not specs**; small-model guidance (`prewalk` = best tool, give context, let it search), markdown is post-code only (4–10 day runs), the `/research→/create→/plan→/ship` workflow, stacking code-foundation shortcuts. → `guiding-small-model.md`, `operating-philosophy.md` |
| `raw/block-002` | 8/11/26 | Tom, harrisony, Rykuuun | **AGENTS.md over-restriction is drift**: "choose simplest", "grow in layers", "long-term decisions", "study established products" are high-risk behavior-steering rules → convert to CI checks, steer **outcomes not behavior**, PR + `gh watch` conclusive loop. → `steer-outcomes-not-behavior.md` |
| `raw/block-003` | 7/26/26 | Tom, 0xSaiya, Rykuuun | **Stacking leverage**: code-as-asset ("code from scratch is cheap, code you hold is valuable"), 2h → 20m → 30s compounding, generic prompt to generalize a good design, try-impossible-first then capture edge cases, browser/computer-use side gigs, "retro capture into skills" verbatim skill. → `stack-your-leverage.md` |
| `raw/block-004` | 7/19/26 | Tom, scarywood75, others | **Mechanical enforcement**: tests for everything deterministic, quality packs, "prompting for what can be mechanically enforced is useless" (researcher-gate example), "Given enough attempts, LLM has no choice but to improve the code." → `enforce-code-quality-mechanically.md` |
| `raw/block-005` | 8/3/26 | scarywood75, Ryukkuun, Sewer56 | **Test/gate methodology**: catch-first tests (pre-fix fail → post-fix pass), broad tests, expand-don't-duplicate + test ledger, files small / themed cohorts, turn repeated scripts into workflows, mechanical gates not star-count. → `how-to-build-good-tests.md`, plus raw `patterns/mem_*` duplicates |

## How to use it in the workflow

- **During `init`** — read `block-002` (how much spine to put in AGENTS.md: steer outcomes, not behavior; the risky one-liners are *real* examples from a Discord QA).
- **During the dev loop** (`workflow-lifecycle/references/dev-loop.md`) — `block-003` is the "capture into skills after a session" ritual; `block-005` is the RED→GREEN test standard for every slice.
- **During `/learn`** — `block-001` + `block-003` are literally how these skills originate: "Recall what we've done… capture everything into skills." Distilling to `~/.agents/skills/<kebab>/` is Pillar 1 & 3 in action.
- **During `/verify`** — `block-004` + `block-005` govern the gate design: gates are unbypassable, tests must catch.

## Provenance

Extracted by the agent from OpenViking session archives (session
`20260822_231822_f198ed/history/archive_001/messages.jsonl`) on 2026-08-26 by
scanning all 2849 session archives for Discord-style threads (`— <date>` markers)
and deduping by content hash. 5 unique threads were found and preserved
byte-verbatim below. All five distilled patterns under `patterns/` came from
`viking://user/default/peers/hermes/memories/patterns/` and were copied byte-identical.
