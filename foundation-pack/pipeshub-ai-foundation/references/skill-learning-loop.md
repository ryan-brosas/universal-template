<!-- capsule-v2 -->
# Skill self-creation loop — how does a finished run become a governed, quality-gated SKILL.md without ever writing itself?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter building agent skill learning must know the exact pipeline stages (extract→evaluate→govern→persist), which stage rejects outright vs queues for humans, and why persistence rides a sub-agent tool call instead of a direct write.

## SkillManager.learn_from_execution — the composition root of learning
**Path/Symbol:** `modules/providers/skills/manager.py:SkillManager.learn_from_execution` (268-307); `_candidate_to_skill_md` (376-390); config `SkillManagerConfig` (62-70) + `_default_governor` precedence (72-77).
**Signature:** `async learn_from_execution(result: AgentResult, trajectory: dict | None = None, decision_trace: list[DecisionTraceEntry] | None = None, session_id: str | None = None) -> list[SkillCandidate]`.
**Data Shape:** Returns every candidate that PASSED evaluation — `status="approved"` (governor cleared it; caller persists via sub-agent) or `status="pending"` (already queued to `_meta/candidates/<id>.json`). Rejected candidates never appear. Caps at `max_candidates` (default 50).

### Decisive source
```python
# manager.py — gate ladder: enabled → should_extract → evaluator → governor
if not self._config.learning_enabled or self._extractor is None:
    return []
if not await self._extractor.should_extract(result):   # cheap deterministic pre-filter
    return []
for candidate in raw_candidates[: self._config.max_candidates]:
    if self._evaluator is not None:
        passed, feedback = await self._evaluator.evaluate_candidate(candidate)
        if not passed:
            logger.info("skill_learning: candidate %r rejected: %s", ...)  # dropped entirely
            continue
    if await self._governor.should_approve(candidate):
        candidate.status = "approved"          # NOT persisted here
    else:
        candidate.status = "pending"
        await self.queue_candidate(candidate)  # _meta/candidates/*.json or store opt-in
```

**Flow:** `SkillLearning` POST_AGENT middleware calls this per successful run → extractor proposes candidates → evaluator quality-gates each → governor decides approved-vs-pending → middleware spawns a `skill_writer` SUB-AGENT whose goal (`_writer_goal`) instructs exactly one `skill_manage(action='create', ...)` call to author+persist; pending ones wait for `get_pending_candidates`/`approve_candidate`/`reject_candidate` (approve renders SKILL.md via `_candidate_to_skill_md`, tagging `source=AGENT_CREATED`).
**Invariant:** The manager NEVER writes a learned skill itself — "everything via tool calls": approved = handed off, pending = queued. Evaluator rejection is silent-drop (not even pending); governor rejection is queue-for-humans. `write_approval=True` beats `auto_approve=True` in `_default_governor`. Manager is the ONLY authority touching store/index/tracker.
**Probe:** `tests/unit/agent_loop_lib/modules/providers/skills/test_manager.py::TestLearnFromExecution` (pins disabled→no extractor call; should_extract False→no extraction; max_candidates truncation; evaluator rejection excludes; governor approve→status approved + empty pending queue; governor reject→pending + queued; session_id stamped). Also `TestCandidateQueueFilesystemFallback` / `TestCandidateQueueViaCandidateStore` / `TestCandidateToSkillMd`.

## LLMSkillExtractor — bounded-reflection structured extraction
**Path/Symbol:** `modules/providers/skills/extractor.py:LLMSkillExtractor` (126-285); `should_extract` (146-150) with `MIN_TOOL_CALLS_FOR_EXTRACTION = 3` (46); `_parse_response` (191-243); `_build_reflection_prompt` (245-258).
**Signature:** ctor `(model, *, min_tool_calls=3, max_candidates=3, reflect_on_malformed_output=True)`; `async extract_candidates(result, trajectory=None, decision_trace=None, existing_catalog=None)`.
**Data Shape:** One structured LLM call returning `{candidates: [{name(kebab), description≤1024, body, category?, subcategory?, tags?, confidence}]}`; empty array explicitly allowed.

### Decisive source
```python
# extractor.py — reflect ONCE with exact errors; only OUTRIGHT-skips are reflection-worthy
candidates, errors = self._parse_response(response, result, trajectory)
if errors and self._reflect_on_malformed_output:
    retry_response = await self._complete(self._build_reflection_prompt(prompt, response, errors))
    ...
# _parse_response: entry-not-a-dict or bad name ⇒ error (retry);
#                  bad confidence/tags ⇒ default our way (0.5 / []), NO retry
name_ok = isinstance(name, str) and _NAME_RE.match(name)
```

**Flow:** `should_extract`: success AND ≥min_tool_calls (cheap, no LLM) → build prompt from goal + tool sequence + output[:2000] (+ trajectory JSON + per-decision reasoning lines + first 50 catalog names as dedup context) → one `complete_structured` call → parse → at most ONE re-prompt listing exactly what was malformed → candidates with kebab-name regex enforced.
**Invariant:** Well-formed output costs exactly ONE call; the Reflexion-style retry fires only on malformed entries and is bounded at one. Field-level salvage (bad confidence → 0.5, stray string tags → [tags]) is NOT an error — only non-object entries and invalid names trigger reflection. Exceptions from the model call return [] (never propagate into the run's tail).
**Probe:** `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_skill_learning.py` (FakeExtractor pins the manager-side contract; middleware-level outcome recording + writer-spawn behavior).

## RubricSkillEvaluator — quality gate + dedup + health ladder
**Path/Symbol:** `modules/providers/skills/evaluator.py:RubricSkillEvaluator.evaluate_candidate` (72-99) and `evaluate_existing` (101-109); thresholds (27-31): underperforming 0.5, min samples 3, deprecate 0.2.
**Signature:** `evaluate_candidate(candidate) -> tuple[bool, str]`; `evaluate_existing(experience) -> tuple["keep"|"refine"|"deprecate", str]`; ctor `(grader=None, rubric=None, index=None, *, dedup_relevance_threshold=0.85, ...)`.
**Data Shape:** Candidate verdict `(passed, feedback)`; existing-skill verdict `(action, reason)` driven by `SkillExperience.success_rate` (=1.0 when zero outcomes).

### Decisive source
```python
# evaluator.py — dedup BEFORE grading (cheaper check first)
if self._index is not None:
    matches = await self._index.search(candidate.description, limit=3)
    near_duplicate = next((m for m in matches if m.relevance >= self._dedup_relevance_threshold), None)
    if near_duplicate is not None:
        return False, f"too similar to existing skill {near_duplicate.skill.name!r}"
...
if experience.success_rate < self._deprecation_threshold:   # <0.2 over ≥3 samples
    return "deprecate", ...
if experience.success_rate < self._underperforming_threshold:  # <0.5
    return "refine", ...
return "keep", ...
```

**Flow:** required-fields check → keyword-search dedup against live index (relevance ≥0.85 ⇒ reject) → RubricGrader.grade on a synthetic trajectory ({goal,name,description,body}) → pass threshold ⇒ accept. Health path: <3 outcomes ⇒ keep ("not enough to judge"); success_rate <0.2 ⇒ deprecate; <0.5 ⇒ refine.
**Invariant:** Extraction proposes, evaluation judges (SRP split). A grading EXCEPTION counts as rejection ("grading failed") — fail closed. Dedup runs BEFORE the expensive grade. Empty experience defaults to healthy (success_rate=1.0), so brand-new skills are never flagged.
**Probe:** same test_manager.py fakes pin the gate order; evaluator thresholds pinned by construction in tests via FakeEvaluator; index-dedup contract cited from source (:76-82).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "learn_from_execution", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "LLMSkillExtractor extract_candidates reflection", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "RubricSkillEvaluator evaluate_candidate", limit: 10 });
```

## Verdict
Adopt the four-stage pipeline (deterministic should_extract → structured extraction with one bounded reflection retry → dedup-before-grade quality gate → governor split approved/pending), the never-persist-directly handoff to a writer sub-agent, and the keep/refine/deprecate health ladder with min-samples hysteresis. Adapt thresholds (3 tool calls, 0.85 dedup, 0.7 pass, 0.5/0.2 health bands) and the SKILL.md rendering to host. Omit the PipesHub-specific wiring (`skills_wiring.py` residual grants) — see run-child-guards capsule for that layer.
