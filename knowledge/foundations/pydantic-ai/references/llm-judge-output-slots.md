<!-- capsule-v2 -->
# LLMJudge output-config fan-out — how does one judge call become score, assertion, or both in the report?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do the `score`/`assertion` OutputConfig slots map a single `GradingOutput{reason, pass_, score}` into named evaluation entries — and what are the naming rules?

## False-sentinel slots + include_both name suffixing
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/common.py:LLMJudge` (:225-284; evaluate :240-281) with `_update_combined_output` (:198-209); four judge variants dispatched from `llm_as_a_judge.py`.
**Signature:** `score: OutputConfig | Literal[False] = False`; `assertion: OutputConfig | Literal[False] = field(default_factory=lambda: OutputConfig(include_reason=True))`.
**Data Shape:** output dict entries keyed by config `evaluation_name` or computed default; values scalar or `EvaluationReason` (reason included only when that slot's `include_reason` is set).

### Decisive source
```python
include_both = self.score is not False and self.assertion is not False
if self.score is not False:
    default_name = f'{evaluation_name}_score' if include_both else evaluation_name
    _update_combined_output(output, grading_output.score, grading_output.reason, self.score, default_name)
if self.assertion is not False:
    default_name = f'{evaluation_name}_pass' if include_both else evaluation_name
    _update_combined_output(output, grading_output.pass_, grading_output.reason, self.assertion, default_name)
```

**Flow:** flag pair (include_input × include_expected_output) selects one of four module-level judge Agents (`judge_output`, `judge_input_output`, `judge_output_expected`, `judge_input_output_expected`) — each a distinct system prompt with few-shot examples → judge returns structured `GradingOutput` → each non-False slot emits an entry. Downstream classification rides the VALUE TYPE: floats/ints land in `report.scores`, bools in `report.assertions`, strings in `report.labels` — so `score=False, assertion=default` yields an assertion named exactly `LLMJudge`, while enabling both renames to `LLMJudge_score` / `LLMJudge_pass` to avoid key collision.
**Invariant:** `False` (not None) is the disabled sentinel because `OutputConfig()` is itself falsy-ish TypedDict usage — a porter switching to Optional[OutputConfig]=None must keep the two-slot semantics distinct. The assertion slot defaults ON (with reasons), score OFF: eval-by-default produces pass/fail, not numbers. Judge agents are imported lazily inside evaluate so pydantic_ai model imports stay off the evaluator import path.
**Probe:** `tests/evals/test_llm_as_a_judge.py::test_build_prompt_section_order_matches_few_shot_examples` (:135-161) pins section order Input→Output→ExpectedOutput→Rubric against the few-shot format; `tests/evals/test_evaluators.py` covers slot fan-out naming.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"LLMJudge build_serialization_arguments","limit":3,"detail":"compact"}'
```
Live check this pass: rank-2 line-exact `common.py 283-284`.

## Verdict
Adopt the slot/sentinel design for any rubric-judge evaluator. Adapt prompt texts and model wiring. Omit the specific judge prompts only if your host has its own grading format — but keep prompt-section-order matching the few-shot examples (test-pinned). Direct tests executed GREEN at pin.
