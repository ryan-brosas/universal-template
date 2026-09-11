<!-- capsule-v2 -->
# Report evaluator data plumbing — how do the four statistical report evaluators source (score, positive) pairs and degrade on empty or degenerate inputs?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What shared extraction contract feeds ConfusionMatrix/PrecisionRecall/ROC-AUC/KS evaluators, and what exactly do they return when data is missing, empty, or single-class?

## literal-keyed extractors + NaN-scalar degradation
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/report_common.py` — `_get_score` (:35-46), `_get_positive` (:49-66), `_extract_scored_cases` (:69-84), `_downsample` (:87-92), `_trapezoidal_auc` (:95-100); evaluators: ConfusionMatrixEvaluator (:106-166), PrecisionRecallEvaluator (:169-230), ROCAUCEvaluator (:233-312), KolmogorovSmirnovEvaluator (:315-396), DEFAULT_REPORT_EVALUATORS (:399-404).
**Signature:** `_get_score(case, score_key, score_from: 'scores'|'metrics') -> float | None`; `_get_positive(case, positive_from: 'expected_output'|'assertions'|'labels', positive_key) -> bool | None`.
**Data Shape:** analyses are a pydantic discriminated union on `type`: `ConfusionMatrix|PrecisionRecall|ScalarResult|TableResult|LinePlot` (`reporting/analyses.py:127-131`).

### Decisive source
```python
if positive_from == 'assertions':
    if positive_key is None:
        raise ValueError("'positive_key' is required when positive_from='assertions'")
    assertion = case.assertions.get(positive_key)
    return assertion.value if assertion else None
...
# every curve evaluator's empty/degenerate arm returns BOTH an empty chart AND:
ScalarResult(title=f'{self.title} AUC', value=float('nan'))
```

**Flow:** per case, score and positivity extracted independently; EITHER missing ⇒ case silently skipped (`_extract_scored_cases`) → PR: anchor point `(recall=0, precision=1)` at max score, then one point per unique threshold (descending), AUC at FULL resolution via trapezoid rule, display points downsampled to `n_thresholds` by even index selection → ROC: TPR/FPR per threshold sorted ascending + dashed `'Random'` diagonal baseline curve → KS: empirical CDFs via `bisect_right` at all unique scores, statistic = running max |pos−neg|, curves use `step='end'` (right-continuous CDFs).
**Invariant:** Four rules porters get wrong: (1) skipping is PER-PAIR — a case with a score but no label vanishes from statistics silently; (2) `positive_key`/`key` requirements raise ValueError only for the literals that need them ('assertions'/'labels'), never for 'expected_output'; (3) empty OR all-same-class inputs return the empty chart PLUS a NaN ScalarResult (never zero, never an exception) so downstream dashboards keep a consistent shape; (4) AUC uses full-resolution points while DISPLAY uses downsampled ones — downsampling is presentation-only.
**Probe:** `tests/evals/test_report_evaluators.py::test_precision_recall_evaluator_basic` (:256-290, perfect separation ⇒ AUC 1.0 + paired ScalarResult), `test_roc_auc_evaluator_all_same_class` (:1093-1109, degenerate ⇒ NaN), `test_precision_recall_evaluator_downsamples` (:315-334, anchor+thresholds 11→3 points).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"PrecisionRecallEvaluator","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 line-exact `report_common.py 187-230`.

## Verdict
Adopt the extractor vocabulary and the chart+NaN-scalar degradation pair wholesale. Adapt analysis model names to your host's report schema. Omit nothing; the four evaluators share enough that porting one without the helpers breaks the others. Direct tests executed GREEN at pin (56-test suite).
