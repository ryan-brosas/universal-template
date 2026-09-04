<!-- capsule-v2 -->
# Eval-plane JSON schema contract — what exact file/field names must eval tooling emit so the harness, grader, aggregator, and viewer interoperate?

**Source:** anthropics/skills Apache-2.0 `main@3b3fad96af16`; Codebase Memory `skills`. **Question:** Which seven JSON files form the skill-creator eval plane's data contract, and where does an exact-name violation silently zero out?

## Seven-schema producer→consumer ladder
**Path/Symbol:** `skills/skill-creator/references/schemas.md` — sections: evals.json (:7), history.json (:39), grading.json (:86), metrics.json (:163), timing.json (:197), benchmark.json (:219), comparison.json (:309) + analysis.json (:384).
**Signature:** n/a (data contract; each section pins field names + nesting).
**Data Shape:** evals.json (skill_name + evals[]{id,prompt,expected_output,files[],expectations[]}) → run dirs emit metrics.json (`<run-dir>/outputs/`), timing.json (`<run-dir>/`) → grading.json merges expectations[] {text,passed,evidence} + summary + execution_metrics + timing + claims + user_notes_summary + optional eval_feedback → benchmark.json nests per-run numbers under `result` with `configuration` ∈ {"with_skill","without_skill"} → comparison-N.json (winner/reasoning/rubric) → analysis.json (post-hoc unblinded).

### Decisive source
```json
"configuration": "with_skill",
"result": {
  "pass_rate": 0.85, "passed": 6, "failed": 1, "total": 7,
  "time_seconds": 42.5, "tokens": 3800, "tool_calls": 18, "errors": 0
}
```
And the warning that makes field names a hard interface:
> **Important:** The viewer reads these field names exactly. Using `config` instead of `configuration`, or putting `pass_rate` at the top level of a run instead of nested under `result`, will cause the viewer to show empty/zero values.

Also the capture-once rule for timing: task notifications carry `total_tokens` and `duration_ms`; "Save these immediately — they are not persisted anywhere else and cannot be recovered after the fact."

**Flow:** author evals.json → executor emits metrics/timing per run → grader emits grading.json (evidence-cited expectation verdicts) → benchmark mode aggregates into benchmark.json (metadata/runs/run_summary/delta as strings like "+0.50") → blind comparator writes comparison-N.json → analyzer unblinds into analysis.json.
**Invariant:** Field names and nesting are consumed verbatim by downstream renderers — renaming or re-nesting yields silent zeros, not errors. `grading_result` vocabulary is closed: "baseline", "won", "lost", "tie".
**Probe:** repo-root deterministic probes (executed 2026-08-26): `grep -n '"configuration"' skills/skill-creator/references/schemas.md` = line 239 only; `grep -n 'viewer reads these field names exactly' skills/skill-creator/references/schemas.md` = line 305; `grep -n 'config" instead of' skills/skill-creator/references/schemas.md` = line 305.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", file_pattern: "*skill-creator*schemas*", limit: 10 });
```
Live result 2026-08-26: Section nodes `evals :7-8`, `history :39-40`, `grading :86-87`, `metrics :163-164`, `benchmark :219-220`, `comparison :309-310`, `analysis :384-385`.

## Verdict
Adopt the seven-file ladder plus exact-field-name discipline for any agent-eval toolchain; keep timing capture at notification time. Adapt storage layout and stat fields to your harness. Omit nothing structural — this is pure interface. Caveat: schemas.md is normative-by-documentation (the scripts are the de-facto enforcement); pairs with eval-harness.md (execution), trigger-matrix-report.md (description loops), benchmark-aggregation-plane.md (aggregation math) — those cover flows, this covers the wire format.
