<!-- capsule-v2 -->
# Grader-Comparator-Analyzer Pipeline — what does each judge agent in the skill-eval pipeline decide, and where does subjectivity get fenced out?

**Source:** anthropics/skills (skill-creator/agents/{grader,comparator,analyzer}.md) Apache-2.0 `main@3b3fad96`; Codebase Memory `skills`. **Question:** How are expectation-grading, blind preference, and improvement-analysis split so no single agent both measures and improves?

## Three agents, three JSON contracts
**Path/Symbol:** `skills/skill-creator/agents/grader.md` (223 lines; PASS/FAIL criteria :85–99 "burden of proof to pass is on the expectation"; claims extraction :43–59 factual/process/quality typing; eval critique :68–79; grading.json schema :106–184 with expectations[].{text,passed,evidence} + summary + claims[] + user_notes_summary + eval_feedback). `comparator.md` (202 lines; blindness contract :7–9/:196; two-dimension 1–5 rubric :39–58 adapted per task type e.g. PDF form → Field alignment/Text readability/Data placement; winner priority order rubric→assertions→TIE :77–86; comparison.json schema :91–172). `analyzer.md` (274 lines; unblinding role :5–7; instruction-following scoring :49–57; suggestions prioritized by would-change-outcome :79–86 with category+priority taxonomy :166–183; benchmark-notes mode :187–274 — observe-only, "DO NOT suggest improvements").
**Signature:** grader: (expectations, transcript_path, outputs_dir) → grading.json. comparator: (output_a_path, output_b_path, eval_prompt, expectations?) → comparison.json {winner: A|B|TIE}. analyzer: (winner/loser skill+transcript paths, comparison_result_path) → analysis JSON.
**Data Shape:** all three write literal-field JSON (same discipline as eval-harness grading): evidence strings must quote, scores are numbers, ties are explicit.

### Decisive source
```markdown
A passing grade on a weak assertion is worse than useless — it creates false
confidence.
...
**Stay blind**: DO NOT try to infer which skill produced which output.
Judge purely on output quality.
...
high: Would likely change the outcome of this comparison
```

**Flow:** executor runs → GRADER grades each expectation against transcript+outputs with cited evidence, extracts and verifies implicit claims, reads executor's user_notes.md, then critiques the EVALS themselves → COMPARATOR judges A/B outputs under blindness (rubric primary, assertion pass-rates secondary, TIE only when genuinely equal) → ANALYZER unblinds: diffs winner vs loser SKILL.md + transcripts, scores instruction-following 1–10, emits improvement_suggestions tagged by category/priority ("would have changed the outcome" = high).
**Invariant:** Separation of powers is the design: the grader never sees which run is "with skill" as a grade input; the comparator never knows provenance; the analyzer never graded — it explains causation after the fact. In benchmark mode the analyzer's role INVERTS to observation-only notes (patterns aggregate metrics hide), explicitly forbidden from improvement suggestions. No partial credit anywhere: every expectation is binary.
**Probe:** No runner (prompt contracts). Deterministic probes: grep the three invariant lines above; verify grader schema requires `evidence` on every expectation entry and comparator's winner vocabulary is exactly A/B/TIE.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "skills", "pattern": "expectations", "limit": 10}'
# resolves `skills/skill-creator/agents/grader.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the three-agent decomposition + literal-field JSON contracts for any LLM-judged eval pipeline. Adapt rubric dimensions to your task domain. Omit the example JSON bodies' content (schema is the contract). Caveat: prose-pinned; complements eval-harness.md (orchestration) and eval-review-viewer.md (human review side).
