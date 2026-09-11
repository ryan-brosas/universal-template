<!-- capsule-v2 -->
# ReportEvaluator contract — how do experiment-wide analyses run, fail, and attach without breaking case-level evaluation?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What is the minimal second evaluator axis (whole-report instead of per-case), and how do its failures isolate?

## ReportEvaluator ABC + analyses/failures report fields
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/report_evaluator.py:ReportEvaluator` (:39-63) + `ReportEvaluatorContext` (:27-36); sink fields `EvaluationReport.analyses` / `.report_evaluator_failures` (`reporting/__init__.py:330-334`); shared serialization base `_base.py:BaseEvaluator`; default set `report_common.py:DEFAULT_REPORT_EVALUATORS` (:399-404).
**Signature:** `evaluate(ctx) -> ReportAnalysis | list[ReportAnalysis] | Awaitable[...]`; `evaluate_async` unwraps via `inspect.iscoroutine`.
**Data Shape:** ctx = `{name, report (full EvaluationReport), experiment_metadata}`; output = discriminated-union analysis models; failure = the same `EvaluatorFailure` carrier used by case evaluators.

### Decisive source
```python
@dataclass(repr=False)
class ReportEvaluator(BaseEvaluator, Generic[InputsT, OutputT, MetadataT]):
    """Base class for experiment-wide evaluators that analyze full reports.

    Unlike case-level Evaluators which assess individual task outputs,
    ReportEvaluators see all case results together and produce
    experiment-wide analyses like confusion matrices, precision-recall curves,
    or scalar statistics."""

    @abstractmethod
    def evaluate(self, ctx) -> ReportAnalysis | list[ReportAnalysis] | Awaitable[...]: ...
```

**Flow:** dataset runs case evaluators first → report assembled with `analyses=[]` and `report_evaluator_failures=[]` → each ReportEvaluator receives the WHOLE report; a returned list appends in order; an exception lands in `report_evaluator_failures` WITHOUT blocking sibling evaluators or the report itself → render prints analyses after the table (`include_analyses`) and failures as a red block.
**Invariant:** The two axes share ONLY the serialization base — ReportEvaluators get no EvaluatorContext, no span tree, no per-case retry; they are pure post-processing over finished cases. A custom one needs just `@dataclass` + `evaluate` returning any union member (e.g. a ScalarResult accuracy). Because they run against the assembled report they can read OTHER evaluators' outputs (`case.scores['confidence']`) — ordering between report evaluators is therefore not guaranteed to see each other's analyses.
**Probe:** `tests/evals/test_report_evaluators.py::test_custom_report_evaluator` (:391-414, 3-case accuracy ScalarResult), `test_async_report_evaluator` (:770), `test_report_evaluator_exception_during_evaluate` (:881) + `test_report_evaluator_failure_does_not_block_others` (:903).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"ReportEvaluator evaluate_async","limit":3,"detail":"compact"}'
```
Live check this pass: resolves line-exact `report_evaluator.py 39-63`.

## Verdict
Adopt the two-axis split (case vs report evaluators) and the failure-isolating append. Adapt analysis model names. Omit nothing. Direct tests executed GREEN at pin (56-test suite incl. isolation cases).
