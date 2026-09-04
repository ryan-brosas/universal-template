<!-- capsule-v2 -->
# Eval Harness — how are with-skill vs baseline runs orchestrated so skill benchmarks are comparable?

**Source:** anthropics/skills Apache-2.0 `main@3b3fad96`; Codebase Memory `skills`. **Question:** What is the exact orchestration contract for measuring whether a skill helps — spawn order, workspace layout, timing capture, and grading schema?

## Parallel A/B eval loop
**Path/Symbol:** `skills/skill-creator/SKILL.md` "Running and evaluating test cases" (Steps 1-4, lines ~169-232); aggregation in `skills/skill-creator/scripts/aggregate_benchmark.py`; viewer in `eval-viewer/generate_review.py` (graph Class `ReviewHandler`, lines 308-384).
**Signature:** `python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>`; viewer: `generate_review.py <workspace>/iteration-N --skill-name <name> [--benchmark benchmark.json] [--previous-workspace <prev>]`.
**Data Shape:** Workspace `<skill>-workspace/iteration-N/eval-<ID>/{with_skill,without_skill|old_skill}/outputs/` plus `eval_metadata.json` per eval (`{eval_id, eval_name, prompt, assertions[]}`), `timing.json` per run (`{total_tokens, duration_ms, total_duration_seconds}`), `grading.json` per run with expectations array using EXACTLY the fields `text`/`passed`/`evidence`.

### Decisive source
```markdown
### Step 1: Spawn all runs (with-skill AND baseline) in the same turn

For each test case, spawn two subagents in the same turn — one with the skill,
one without. This is important: don't spawn the with-skill runs first and then
come back for baselines later. Launch everything at once so it all finishes
around the same time.
...
### Step 3: As runs complete, capture timing data
When each subagent task completes, you receive a notification containing
`total_tokens` and `duration_ms`. Save this data immediately to `timing.json`
... This is the only opportunity to capture this data — it comes through the
task notification and isn't persisted elsewhere.
```

**Flow:** Save 2-3 realistic prompts to `evals/evals.json` (no assertions yet) → snapshot the old skill if improving (`cp -r <skill> <workspace>/skill-snapshot/`) → spawn ALL with-skill + baseline subagents in one turn (baseline = no skill when creating, old version when improving) → draft assertions while runs execute → persist each completion notification's tokens/duration to `timing.json` on arrival → grade against assertions (script where checkable) → aggregate into benchmark.json with mean ± stddev deltas → analyst pass for non-discriminating assertions / high-variance evals → launch viewer for human review → improve from feedback → iterate.
**Invariant:** Baseline and treated runs must be spawned together (temporal comparability); grading field names are load-bearing ("the viewer depends on these exact field names"); empty user feedback means satisfied — improvements target only cases with specific complaints.
**Probe:** `skills/skill-creator/scripts/aggregate_benchmark.py` produces `benchmark.json`/`benchmark.md`; `references/schemas.md` pins the JSON schemas the viewer consumes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "aggregate benchmark pass_rate", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "skills", query: "ReviewHandler generate_review", limit: 5 });
```

## Verdict
Adopt: same-turn A/B spawning, notification-captured timing (single opportunity), literal grading schema, test-set expansion after convergence — a general recipe for measuring any prompt/harness change. Adapt subagent mechanics and viewer to your harness (the doc itself carries Claude.ai/Cowork fallback branches). Omit blind-comparison mode unless you need adversarial A/B judging. Caveat: orchestration is prose-pinned; the executable surface is the two scripts above.
