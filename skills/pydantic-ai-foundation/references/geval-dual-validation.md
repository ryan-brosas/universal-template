<!-- capsule-v2 -->
# GEval score-range validation — where must an integer-scored judge validate its range, and why twice?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When porting a chain-of-thought integer-score evaluator, which of construction time vs judge-response time owns the score_range checks?

## __post_init__ pre-flight + post-run response guard
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/common.py:GEval.__post_init__` (:314-318) + `evaluate` (:320-332); mirrored in `llm_as_a_judge.py:judge_g_eval` (:355-358 construction checks, :376-377 response check).
**Signature:** `score_range: tuple[int, int] = (1, 5)`; raises `ValueError('`score_range` must satisfy min < max, got ...')`.
**Data Shape:** output = `GEvalOutput{reason: str, score: int}` via a dedicated Agent with JSON-only system prompt; rubric embeds numbered steps and the inclusive bounds sentence.

### Decisive source
```python
# common.py — fail fast at construction
def __post_init__(self):
    if self.score_range[0] >= self.score_range[1]:
        raise ValueError(f'`score_range` must satisfy min < max, got {self.score_range!r}')
    if not self.evaluation_steps:
        raise ValueError('`evaluation_steps` must contain at least one step')

# llm_as_a_judge.py — the LLM can still disobey
if not score_range[0] <= result.score <= score_range[1]:
    raise ValueError(f'Judge returned score {result.score}, outside the requested `score_range` {score_range!r}')
```

**Flow:** dataclass construction validates config shape (min<max, ≥1 step) → evaluate delegates to `judge_g_eval`, which RE-validates (it is also a public function callable without the GEval wrapper) → builds rubric text: criteria, numbered steps, "single integer between X and Y inclusive" → prompt sections ordered Input→Output→Rubric → structured output parsed → inclusive-bounds re-check of the returned score → returned as `EvaluationReason(value=score, reason=...)`.
**Invariant:** The docstring records the deliberate divergence from the G-Eval paper: no log-prob weighting over score tokens — a direct integer is requested for provider-agnosticism. The out-of-range judge response raises ValueError (which `run_evaluator` converts to an `EvaluatorFailure` row), it does NOT clamp or retry — clamping would fabricate agreement. Note `min < max` (not ≤): a degenerate single-value scale is rejected.
**Probe:** `tests/evals/test_llm_as_a_judge.py::test_build_prompt_section_order_matches_few_shot_examples` (:135-161); out-of-range and empty-steps branches covered by the judge test suite.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"judge_g_eval","limit":3,"detail":"compact"}'
```
Live check this pass: `_build_prompt` rank-1 line-exact `llm_as_a_judge.py 262-288`; GEval class resolves via common.py retrieval battery.

## Verdict
Adopt both validation sites — they protect different callers (dataclass users vs direct judge_* callers). Adapt the rubric wording. Omit the log-prob weighting deliberately (documented upstream trade-off). Direct tests executed GREEN at pin.
