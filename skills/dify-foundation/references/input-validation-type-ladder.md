<!-- capsule-v2 -->
# input-validation-type-ladder — How do untrusted form inputs become typed, safe variables?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What is the exact coercion/validation order for user form inputs before they reach a workflow?

## Per-variable validation → sanitize → file conversion → shape rejection
**Path/Symbol:** `api/core/app/apps/base_app_generator.py:BaseAppGenerator._prepare_user_inputs` (:129-203), `_validate_inputs` (:205-305), `_sanitize_value` (:307-310).
**Signature:** `_prepare_user_inputs(*, user_inputs, variables, tenant_id, strict_type_validation=False) -> Mapping[str, Any]`; `_validate_inputs(*, variable_entity, value)`.
**Data Shape:** Output values: str/int/float/bool/None/File (dict→File via file_factory with per-variable FileUploadConfig allowlists) or list[File] for FILE_LIST; unknown dict/list shapes raise ValueError naming offending keys.

### Decisive source
```python
def _validate_inputs(self, *, variable_entity, value):
    if value is None:
        if variable_entity.required:
            raise ValueError(f"{variable_entity.variable} is required in input form")
        value = variable_entity.default
        if value is None:
            return None

    # Treat empty placeholders for optional file inputs as unset
    if variable_entity.type in {FILE, FILE_LIST} and not variable_entity.required:
        if isinstance(value, str) and not value:
            return None                      # empty string = unset; [] still passes for lists

    ...
    case VariableEntityType.NUMBER:
        match value:
            case int() | float(): return value
            case str():
                if not value.strip(): return None
                try:
                    return float(value) if "." in value else int(value)
                except ValueError:
                    raise ValueError(f"{variable_entity.variable} ... must be a valid number")
    case VariableEntityType.CHECKBOX:
        match value:
            case str():
                normalized_value = value.strip().lower()
                if normalized_value in {"true", "1", "yes", "on"}: value = True
                elif normalized_value in {"false", "0", "no", "off"}: value = False
            case int() | float():
                if value == 1: value = True
                elif value == 0: value = False
```
```python
# _prepare_user_inputs tail: reject leftover raw dicts/lists outside FILE/JSON_OBJECT/FILE_LIST
invalid_dict_keys = [k for k, v in user_inputs.items()
                     if isinstance(v, dict) and entity_dictionary[k].type not in {FILE, JSON_OBJECT}]
if invalid_dict_keys:
    raise ValueError(f"Invalid input type for {invalid_dict_keys}")
...
user_inputs = {k: self._sanitize_value(v) for k, v in user_inputs.items()}   # strips \x00 from every string
```

**Flow:** filter to declared variables (required-check; default-fill continues INTO type conversion) → per-type ladder (string types must be str + length cap; SELECT membership; NUMBER int/float-from-str; CHECKBOX truthy-string/number normalization; JSON_OBJECT dict-only) → `\x00` scrub on all strings → dict inputs built into File objects under that variable's upload allowlist → final sweep rejects any residual dict/list outside the sanctioned types.
**Invariant:** Defaults pass through the SAME validation as user values (no trust shortcut); empty-string optional-file ≡ unset but empty-LIST stays a legal FILE_LIST value; checkbox non-normalizable strings stay strings silently (no raise); the final invalid-shape sweep is what makes the output contract enforceable rather than aspirational.
**Probe:** `grep -c 'normalized_value' core/app/apps/base_app_generator.py` → 3; `grep -cF 'replace("\x00", "")' core/app/apps/base_app_generator.py` → 1; direct tests `tests/unit_tests/core/app/apps/test_base_app_generator.py::test_prepare_user_inputs_rejects_invalid_dict_inputs`, `::test_prepare_user_inputs_rejects_invalid_list_inputs`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "BaseAppGenerator _prepare_user_inputs validate inputs file", limit: 10 });
```

## Verdict
Adopt the ladder ordering (validate → sanitize → convert files → shape-sweep). Adapt type enum and truthy vocabularies. Omit strict_type_validation nuances unless you expose a service API.
