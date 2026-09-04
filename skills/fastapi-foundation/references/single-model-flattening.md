<!-- capsule-v2 -->
# Single-model flattening — How do Pydantic-model query/header params expand into per-field validation without losing the model wrapper?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** When exactly is a lone BaseModel param in query/header/cookie treated as "the fields ARE the params", and what must a porter preserve so required-ness and extra keys behave?

## Flatten-on-single-model rule
**Path/Symbol:** `fastapi/dependencies/utils.py:_get_flat_fields_from_params` (157–166) + `request_params_to_args` (780–866, model branch 790–850) + `_get_multidict_value` (749–777); OpenAPI twin `_get_flat_fields_from_params` reuse in `fastapi/openapi/utils.py:169–172`.
**Signature:** `_get_flat_fields_from_params(fields: list[ModelField]) -> list[ModelField]`; `request_params_to_args(fields, received_params) -> tuple[dict[str, Any], list[Any]]`.
**Data Shape:** branch condition `len(fields) == 1 and lenient_issubclass(first.field_info.annotation, BaseModel)`; extraction set becomes `get_cached_model_fields(model)` (cached so repeated requests don't rebuild FieldInfos).

### Decisive source
```python
    if len(fields) == 1 and lenient_issubclass(first_field.field_info.annotation, BaseModel):
        fields_to_extract = get_cached_model_fields(first_field.field_info.annotation)
        single_not_embedded_field = True
        # If headers are in a Pydantic model, the way to disable convert_underscores
        # would be with Header(convert_underscores=False) at the Pydantic model level
        default_convert_underscores = getattr(first_field.field_info, "convert_underscores", True)
    ...
    for key in received_params.keys():          # collect UNDECLARED keys for model-level extras
        if key not in processed_keys:
            ...params_to_process[key] = value   # single-element getlist unwraps to scalar
    if single_not_embedded_field:
        v_, errors_ = _validate_value_with_model_field(
            field=first_field, value=params_to_process, values=values,
            loc=(field_info.in_.value,))
        return {first_field.name: v_}, errors_  # ONE loc ("query",) not ("query","field")
```

**Flow:** flatten → per-field alias lookup (`getlist` for sequence-typed non-JSON fields against ImmutableMultiDict/Headers; empty-string Form values treated as missing) → undeclared received keys folded into `params_to_process` (feeds `model_config extra`) → validate the WHOLE model once with location `(in_,)` → return under the original parameter name.
**Invariant:** (1) Error locations differ by shape — flattened models report `("query",)` while individual scalars report `("query", alias)`; porting one style to the other changes every client's error payload. (2) Header underscore conversion applies per extracted field using the MODEL-level `convert_underscores`, and BOTH the converted alias and original alias are marked processed so the raw alias can't sneak back as an "extra". (3) Missing required flattened fields produce one error per field via the same `_get_multidict_value` default/required ladder used for plain params.
**Probe:** `tests/test_query_param_models.py` + `tests/test_header_param_models.py` (+ `test_cookie_param_models.py`) pin model-param validation, aliases, convert_underscores off-switch, and extra-forbidden errors.
