<!-- capsule-v2 -->
# evaluation run pipeline — how do dataset expansion, API batching, and labeler invocation interleave with persistence?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I run an eval harness that persists intermediate rows before labeling, so crashes leave usable partial results?

## two-phase executor + XOR dataset contract
**Path/Symbol:** `src/ell/evaluation/evaluation.py:Evaluation` (`__init__` validation :100-129; `run` :132-211; `_process_single` :214-237; `prepare_run_params` :239-260; `prepare_run_dataset` :262-275); helpers in `src/ell/evaluation/util.py:get_lmp_output` (:9-25), `validate_callable_dict` (:29-56).
**Signature:** `run(self, lmp, *, n_workers=1, use_api_batching=False, api_params=None, verbose=False, **additional_lmp_params) -> EvaluationRun`.
**Data Shape:** datapoints are dicts with optional `"input"` (list→positional, dict→kwargs, None→paramless); labelers become `(name, EvaluationLabelerType)` pairs wrapping wrapped callables.

### Decisive source
```python
# evaluation.py:101-104 — exactly one expansion source
if self.dataset is None and self.n_evals is None:
    raise ValueError("Either dataset or n_evals must be set")
if self.dataset is not None and self.n_evals is not None:
    raise ValueError("Either dataset or n_evals must be set, not both")
```

```python
# evaluation.py:264-273 — batching folds repetition into the API's n
if use_api_batching:
    # we need to collate on unique datapoints here if possible; note that n_evals can never be set.
    run_api_params["n"] = self.samples_per_datapoint * (self.n_evals or 1)
else:
    dataset = sum(
        [
            [data_point] * self.samples_per_datapoint * (self.n_evals or 1)
            for data_point in dataset
        ], []
    )
```

**Flow:** labeler wrap-up converts plain callables to tracked FUNCTION LMPs (skipping already-tracked ones via `__ell_track__`) and asserts at least one label exists while hard-failing `annotations` ("not supported yet"). Run: persist evaluation → start run row → phase 1 executor maps datapoints through `_process_single`, which calls the LMP with `_get_invocation_id=True` and returns PARTIALS (labels not yet applied); each completed output is written immediately via `write_evaluation_run_intermediate`; phase 2 submits those partials to apply labelers (each labeler itself invoked with `_get_invocation_id=True`) and collects results; finally summaries + success flag persist. Global `config.verbose` is saved/set/restored around the whole run.
**Invariant:** intermediates are persisted BEFORE labeling so partial results survive failure; invalid input shapes raise with the offending type named (`"Invalid input type: <class 'int'>"`).
**Probe:** `tests/test_evaluation.py:test_evaluation_run_with_invalid_input` (:71-77) pins the ValueError message; `test_evaluation_run_with_missing_params` (:79-89) pins paramless invocation returning one result; `test_evaluation_initialization` (:30-) pins label assembly from metrics+criterion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "evaluation run dataset batching", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.evaluation.evaluation.Evaluation.prepare_run_dataset @ src/ell/evaluation/evaluation.py:262-275
```

## Verdict
Adopt the two-phase write-then-label pipeline and the dataset-XOR-n_evals contract. Adapt the batch mode if your vendor lacks an `n` parameter. Omit the annotations branch entirely until you implement it — shipping a dead code path invites silent no-op labels.
