<!-- capsule-v2 -->
# best_of_n tool surface (read-only candidates + judge; kernel lives in agent/best_of_n.py)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What does the best_of_n TOOL own vs the run_best_of_n kernel it delegates to — and what usage contract keeps N parallel runs safe?

## Path/Symbol
`tools/builtin/coordination/best_of_n.py` — whole file, 104L; class docstring (:13–26), `handle()` (:99–101). Kernel: `agent/best_of_n.py::run_best_of_n` (mined pass 6 as `best-of-n-judge` — judge degradation + winner-index mapping live THERE).

## Signature
`handle()` = `return await run_best_of_n(ctx.agent, call, ctx.goal, ctx.turn_index, ctx.started_at)` — thin special-route adapter so the kernel stays unit-testable without a full Agent/turn loop (same convention as other special routes).

## Data Shape
Args: `{role, goal, n (2–5, required), criteria (required), tools?, model?}`. Tagged TAG_SPAWN (rides spawn-depth guard/config scoping/cancellation propagation unchanged — same RuntimeRouter path as spawn_agent).

### Decisive source
```python
Run-level best-of-N: launches N independent candidate sub-agent runs
for the SAME goal in parallel ..., then one judge LLM call picks a winner.
This is the loop's answer to in-loop tree search (LATS/ToT) WITHOUT changing
the turn-loop kernel — branching happens across whole runs, never mid-trajectory.
```
Tool description: *"USE ONLY when the output is judgeable and candidates have no critical side effects — give candidates read-only/idempotent tools ... since every candidate's actions happen regardless of who wins; there is no undo for the ones that lose."*

**Flow:** model judges a goal worth N attempts → N parallel run_child candidates → judge picks winner by criteria → winner's output becomes the tool result. Branching at RUN granularity only.

**Invariant:** The safety contract is stated where the model commits to it: all-N side effects happen unconditionally (losers aren't rolled back) ⇒ read-only/idempotent candidate toolsets are mandatory guidance, not a suggestion. Run-level branching keeps the turn-loop kernel untouched — an alternative to in-trajectory tree search.

**Probe:** `tests/unit/agent_loop_lib/agent/test_best_of_n.py` — exercises `run_best_of_n` end-to-end with duck-typed agent double + `_judge` branch unit tests (judge degradation ladder pinned at :1–40 and throughout). Tool file itself needs no test beyond the delegation line (coverage caveat noted).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["BestOfNTool","run_best_of_n","_run_one_candidate"]'
```

## Verdict
Adopt run-granularity branching with the read-only-candidates contract surfaced in the tool description; reuse the existing best-of-n-judge capsule for judge semantics — this capsule pins only the tool-side surface.
