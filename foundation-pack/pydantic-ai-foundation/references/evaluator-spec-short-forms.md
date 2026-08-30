<!-- capsule-v2 -->
# BaseEvaluator spec serialization — how do evaluator instances round-trip through YAML/JSON datasets in three short forms?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does a dataclass evaluator instance become `{'Name': arg}` / `'Name'` / `{'Name': {kwargs}}` on dump — and why can a single non-default field still serialize as a dict?

## as_spec argument-form selection ladder
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/_base.py:BaseEvaluator.as_spec` (:70-89) + `build_serialization_arguments` (:91-110); forms defined by `EvaluatorSpec = NamedSpec` (`evaluators/spec.py:8`, shared `pydantic_ai._spec.NamedSpec`).
**Signature:** `as_spec(self) -> EvaluatorSpec`; `build_serialization_arguments(self) -> dict[str, Any]`.
**Data Shape:** raw arguments = dataclass fields minus defaults (both `default` and `default_factory` compared by `==`); serialized shape = `None | tuple[Any] | dict[str, Any]` under key `arguments`, plus `name` from `get_serialization_name()` (class name).

### Decisive source
```python
if len(raw_arguments) == 0:
    arguments = None
elif len(raw_arguments) == 1:
    # Only use the compact tuple form if the single non-default field is the first
    # dataclass field, since the tuple form passes the value as the first positional arg.
    first_field_name = fields(self)[0].name
    key = next(iter(raw_arguments))
    if key == first_field_name and not serializes_as_string_keyed_dict(value):
        arguments = (value,)
    else:
        arguments = raw_arguments
else:
    arguments = raw_arguments
```

**Flow:** dump → pydantic `model_serializer(mode='plain')` calls `to_jsonable_python(self.as_spec(), ...)` (:57-68) → `build_serialization_arguments` walks `fields(self)` skipping value==default entries → form ladder picks `None` / 1-tuple / kwargs dict.
**Invariant:** The tuple form is only legal when the single remaining field is ALSO the first declared field — otherwise positional reconstruction would bind the value to the wrong parameter. A second guard excludes values that themselves serialize as string-keyed dicts (they would be indistinguishable from the kwargs form on re-parse). Subclasses customize by overriding `build_serialization_arguments` only (e.g. `LLMJudge` swaps a Model instance for its id via `_serialize_model_as_string`).
**Probe:** `tests/evals/test_evaluator_base.py::test_evaluator_serialization` (:253-305) — all-defaults → `{'arguments': None, 'name': ...}`, first-field override → tuple `[100]`, non-first-field override (`optional='test'`) → dict form, multiple overrides → full dict; plus `use_short_form` context snapshots.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"build_serialization_arguments","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 line-exact `_base.py 91-110`.

## Verdict
Adopt the whole ladder — it is what makes dataset files writable by hand. Adapt the `NamedSpec` wire type to your host's config schema. Omit nothing; note the deliberate asymmetry that default-exclusion uses `==` (not `is`), so evaluators whose fields carry objects with surprising `__eq__` must override `build_serialization_arguments`. Direct test executed GREEN at pin (suite `test_evaluator_base.py`, 18 passed).
