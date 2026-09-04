<!-- capsule-v2 -->
# Pydantic validator — why does validation round-trip through JSON, and how are errors rendered?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How does the Python validator turn a dict into a strict typed instance and produce repair-ready error text?

## TypeChatValidator
**Path/Symbol:** `python/src/typechat/_internal/validator.py:11-67` (`TypeChatValidator.validate_object` :27-45; `_handle_error` :48-67).
**Signature:** `__init__(self, py_type: type[T])` builds `pydantic.TypeAdapter(py_type)` once; `validate_object(self, obj: object) -> Result[T]`.
**Data Shape:** input is the parsed JSON (dicts/lists/scalars); output on success is a REAL typed instance (dataclass/TypedDict-typed), not the raw dict.

### Decisive source
```py
try:
    # TODO: Switch to `validate_python` when validation modes are exposed.
    # https://github.com/pydantic/pydantic-core/issues/712
    # We'd prefer to keep `validate_object` as the core method and
    # allow translators to concern themselves with the JSON instead.
    # However, under Pydantic's `strict` mode, a `dict` isn't considered compatible
    # with a dataclass. So for now, jump back to JSON and validate the string.
    json_str = pydantic_core.to_json(obj)
    typed_dict = self._adapted_type.validate_json(json_str, strict=True)
    return Success(typed_dict)
except pydantic.ValidationError as validation_error:
    return _handle_error(validation_error)
```
**Flow:** obj → canonical JSON bytes → `validate_json(strict=True)` → Success(instance) | Failure(rendered).
**Invariant:** STRICT mode is load-bearing twice over: it rejects model-invented type coercions ("2" ≠ 2) AND forces the JSON round-trip because in strict mode a plain dict is not compatible with a dataclass — `validate_python(obj)` would spuriously fail. Porters who "simplify" to validate_python break every dataclass schema. `_handle_error` renders each issue as `` Validation path `a.b` failed for value `<json>` because:\n  <msg>`` (root issues get "Root validation" prefix) and prefixes "Several possible issues may have occurred with the given data.\n\n" when >1 — wording that test snapshots pin.
**Probe:** `grep -c 'validate_json(json_str, strict=True)' python/src/typechat/_internal/validator.py` (=1). EXECUTED live this pass: `/tmp/tc-p3-run/bin/python -m pytest tests/test_validator.py -vv` from `python/` at pin 83caa124 → `tests/test_validator.py::test_dict_valid_as_dataclass PASSED` (dict → `Success(Example(a='hello!', b=42, c=True))` dataclass equality), part of the full **22 passed, 17 snapshots** fleet run under Python 3.14.7.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"TypeChatValidator validate_object pydantic","limit":4}'
// rank1 Method validator.py 27-45; rank2 shows example-side subclass pattern (math/program.py 112-116)
```

## Verdict
Adopt strict-mode-via-JSON exactly (with the upstream TODO comment so future porters know why); adapt error prose freely but keep per-issue paths+values — they are what make one-shot repair work; omit the multi-issue banner only if your prompts tolerate ambiguity.
