<!-- capsule-v2 -->
# Accumulate-then-ExceptionGroup loader — why does one bad evaluator spec report ALL failures (first three) instead of the first?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How should a file loader surface multiple independent resolution errors without failing on the first?

## Per-spec accumulation with first-3 truncation
**Path/Symbol:** `pydantic_evals/pydantic_evals/dataset.py:_from_dataset_model` (:668-745).
**Signature:** `_from_dataset_model(dataset_model, custom_evaluator_types, custom_report_evaluator_types, default_name) -> Self`.
**Data Shape:** Three sequential resolution loops — dataset evaluators, report evaluators, per-case evaluators — each appending ValueError to one shared `errors: list`.

### Decisive source
```python
errors: list[ValueError] = []
for spec in dataset_model.evaluators:
    try:
        dataset_evaluator = _load_evaluator_from_registry(registry, spec, 'evaluator',
                                                          'custom_evaluator_types', context='dataset')
    except ValueError as e:
        errors.append(e); continue          # keep resolving siblings
    dataset_evaluators.append(dataset_evaluator)
# ... same for report evaluators, then per-case rows (context=f'case {row.name!r}') ...
if errors:
    raise ExceptionGroup(f'{len(errors)} error(s) loading evaluators from registry', errors[:3])
name = dataset_model.name if dataset_model.name is not None else default_name
if name is None:
    raise ValueError('Dataset name is required: provide one in the serialized data or via `default_name`.')
result = cls(name=name, cases=cases, report_evaluators=report_evaluators)
result.evaluators = dataset_evaluators   # init takes report_evaluators but NOT evaluators
```

**Flow:** Every spec gets a chance regardless of earlier failures → single ExceptionGroup whose message COUNTS all errors but whose payload carries only `errors[:3]` → then name-required check → construct → post-construction assignment of dataset-level evaluators.
**Invariant:** The header count is authoritative (`len(errors)`); payload truncation at 3 is deliberate noise control. A porter who raises on first failure turns one typo into a fix-retry-fix loop; who truncates the count lies about remaining problems. Note the constructor asymmetry: dataset-level evaluators bypass __init__ and are assigned after — replicate or widen the signature deliberately, not accidentally.
**Probe:** `tests/evals/test_dataset.py::test_from_text_failure` (:1141-1201) asserts the EXACT repr: `'2 error(s) loading evaluators from registry'` with two ValueErrors (one context='dataset', one per-case), both unknown-name and missing-arg variants.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_from_dataset_model errors ExceptionGroup", limit: 5 });
```
Live check this pass: search_graph resolved Dataset method map (:557-913) before whole-file read; coverage clean for dataset.py.

## Verdict
Adopt accumulate→count-in-message→truncate-payload ExceptionGroup loading. Adapt which loops feed the shared error list; keep per-item context strings ('for case X') so users can locate offenders. Omit nothing else.
