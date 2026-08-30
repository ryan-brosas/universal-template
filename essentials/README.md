# Essentials — Operating Philosophy

The operating philosophy (from mentor Tom and scarywood75) that guides how we work.
These documents define *how* we approach development and automation without over-restricting agent behavior.

## The Synthesis & Objectives (Start Here)
- `operating-philosophy.md` — The authoritative unified manifesto combining all four pillars, the Catch-First test methodology, and the complete development flywheel.
- `objectives.md` — Concrete, actionable tactical & strategic objectives derived from each pillar, driving our roadmap, skill development, testing harness, and cron marathons.

## The Core Pillars & Methodology
- `guiding-small-model.md` — **Pillar 1:** Code is ground truth, skills are the shortcuts. How to feed the small model (`deepseek-flash`) ground truth and run the Two-Pass Learning Protocol so it executes without hallucinations or mistakes.
- `steer-outcomes-not-behavior.md` — **Pillar 2:** Don't over-restrict the agent with behavioral system prompt rules. Let the agent execute with full autonomy, and enforce quality at the outcome boundary via mechanical CI checks and conclusive PR loops.
- `stack-your-leverage.md` — **Pillar 3:** Code is your compounding asset. Stack proven code into reusable skills, harvest edge cases post-session, and accelerate velocity ($2\text{ hrs} \to 20\text{ mins} \to 30\text{ secs}$).
- `enforce-code-quality-mechanically.md` — **Pillar 4:** Enforce code quality with unbypassable tests, gates, and CI, not prompting. Strip deterministic responsibility from the LLM.
- `how-to-build-good-tests.md` — **Test & Gate Methodology:** A test is only good if it can catch (un-fixed RED $\to$ fixed GREEN). Build broad tests, expand instead of duplicating, maintain a test ledger, and promote manual catches to CI workflows.

## The Context & Memory Plane
- `openviking-foundation.md` — OpenViking's role (durable experience/context memory), retrieval surface, and the **ingest protocol** for new source material (Discord exports, doc sets, chat logs). Machine facts (endpoint, storage, corpus size) are probed at runtime, not frozen here. Discord status: found & harvested (see `discord-material/`).
- `discord-material/` — **The verbatim Discord threads** (raw/ + patterns/) these pillars were synthesized from: code-is-ground-truth (8/21), steer-outcomes-not-behavior (8/11), stacking-leverage (7/26), mechanical gates (7/19), catch-first tests (8/3). `README.md` maps each thread → its pillar doc. Quote these verbatim when developing the workflow further.
## How to Use in Practice
- Read `operating-philosophy.md` before planning architecture or starting complex tasks.
- Track progress against `objectives.md` during milestone planning.
- Squeezing repos into per-repo foundation leaves (`skills/*-foundation`) **IS** Pillar 1 & 3 in action.
- The 7-gate `foundations-workflow` and PR conclusive loops **ARE** Pillar 2 & 4 in action.
- Catch-First testing (RED $\to$ GREEN) is the verification standard across all prompts and tools.
