<!-- capsule-v2 -->
# Own-dict @dataclass gate — why does an evaluator subclass that INHERITS a dataclass parent get rejected at registration?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What makes a custom evaluator class eligible for registry/schema inclusion — and why check the class __dict__ instead of isinstance dataclass-ness?

## `'__dataclass_fields__' in cls.__dict__` membership test
**Path/Symbol:** `pydantic_evals/pydantic_evals/dataset.py:_get_evaluator_registry._validate_evaluator` (:1318-1324), applied by `_spec.py:build_registry` and again inside `model_json_schema_with_evaluators` (:797-844).
**Signature:** `_validate_evaluator(cls) -> None` (closure over base_class + label).
**Data Shape:** Two gates, both raising plain ValueError with the label interpolated.

### Decisive source
```python
def _validate_evaluator(cls: type[BaseEvalT]) -> None:
    if not issubclass(cls, base_class):
        raise ValueError(f'All custom {label} classes must be subclasses of {base_class.__name__}, but {cls} is not')
    if '__dataclass_fields__' not in cls.__dict__:      # OWN dict, not inherited!
        raise ValueError(f'All custom {label} classes must be decorated with `@dataclass`, but {cls} is not')
```

**Flow:** Registry build AND schema generation both construct registries through this validator, so a non-dataclass custom type is rejected whether you are loading a file or generating the editor schema. The own-dict test means: a class inheriting from a decorated dataclass parent FAILS, because `__dataclass_fields__` sits on the parent's `__dict__`, and the child never re-ran the decorator — its constructor semantics were never regenerated for its own fields.
**Invariant:** Eligibility = subclass of base AND self-decorated. Using `isinstance(cls, type)` dataclass protocols or `dataclasses.is_dataclass(cls)` would wrongly admit inherited-decoration children whose field set doesn't match their own attributes.
**Probe:** `tests/evals/test_dataset.py::test_add_invalid_evaluator` (:1683-1699) pins BOTH messages via `model_json_schema_with_evaluators((NotAnEvaluator,))` → "must be subclasses of Evaluator…" and `((SimpleEvaluator,))` → "must be decorated with `@dataclass`…".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "validate evaluator dataclass fields registry", limit: 6 });
```
Live check this pass: search_graph Class sweep mapped `_get_evaluator_registry` (:1310-1332); decisive range read directly; coverage clean.

## Verdict
Adopt the two-gate validation with the own-dict membership test verbatim. Adapt the base class and message nouns. Omit nothing — the subtlety IS the seam.
