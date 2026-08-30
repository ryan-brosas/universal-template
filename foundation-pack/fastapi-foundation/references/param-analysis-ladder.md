<!-- capsule-v2 -->
# Param analysis ladder — How is a raw signature parameter classified into query/path/body/dependency?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** Given an endpoint parameter with arbitrary `Annotated`/default combinations, what decides whether it becomes a Query, Path, Body, a sub-Dependant, or special injection — and in which precedence order?

## analyze_param decision ladder
**Path/Symbol:** `fastapi/dependencies/utils.py:analyze_param` (lines 381–547) + `get_dependant` dispatch (294–346) + `add_non_field_param_to_dependency` (350–371).
**Signature:** `analyze_param(*, param_name, annotation, value, is_path_param) -> ParamDetails(type_annotation, depends: params.Depends | None, field: ModelField | None)`.
**Data Shape:** `ParamDetails` triad; `get_dependant` then routes: `depends` → child Dependant; special types (`Request`/`WebSocket`/`HTTPConnection`/`Response`/Starlette `BackgroundTasks`/`SecurityScopes`) → recorded param-name slots; `params.Body` → `body_params`; else bucketed by `field_info.in_` into path/query/header/cookie.

### Decisive source
```python
    if get_origin(use_annotation) is Annotated:
        annotated_args = get_args(annotation)
        type_annotation = annotated_args[0]
        fastapi_annotations = [a for a in annotated_args[1:] if isinstance(a, (FieldInfo, params.Depends))]
        fastapi_specific_annotations = [a for a in fastapi_annotations
            if isinstance(a, (params.Param, params.Body, params.Depends))]
        if fastapi_specific_annotations:
            fastapi_annotation = fastapi_specific_annotations[-1]   # LAST wins
    ...
    elif field_info is None and depends is None:
        default_value = value if value is not inspect.Signature.empty else RequiredParam
        if is_path_param:
            field_info = params.Path(annotation=use_annotation)
        elif is_uploadfile_or_nonable_uploadfile_annotation(type_annotation) or \
             is_uploadfile_sequence_annotation(type_annotation):
            field_info = params.File(annotation=use_annotation, default=default_value)
        elif not field_annotation_is_scalar(annotation=type_annotation):
            field_info = params.Body(annotation=use_annotation, default=default_value)
        else:
            field_info = params.Query(annotation=use_annotation, default=default_value)
```

**Flow:** unpack PEP 695 `TypeAliasType` → read `Annotated` metadata (last FastAPI-specific annotation wins; FieldInfo defaults must NOT be set inside Annotated — assert forces `=` default style) → accept legacy default-value forms (`value is params.Depends(...)` / `is FieldInfo`) with mutual-exclusion asserts → bare `Depends()` with no callable binds the TYPE as the dependency (`dataclasses.replace(depends, dependency=type_annotation)` — this is how class-based deps work) → only when NO explicit Depends, non-param Starlette types become injections (explicit `Depends()` over them means "call it and use the return") → fallback inference ladder: path name ∈ path template ⇒ Path; UploadFile/sequence ⇒ File; non-scalar ⇒ Body; scalar ⇒ Query. Post-pass: header/cookie aliases get underscore→dash conversion via `convert_underscores`; path params asserted scalar.
**Invariant:** (1) Inference happens ONLY when neither Annotated nor default carried a FastAPI annotation — an explicit `Query()` never silently degrades to Body. (2) Non-scalar ⇒ Body is the default, so a bare `dict`/model param becomes the request body. (3) `Annotated` FieldInfo + `=` default are COMBINED (default copied onto the copied FieldInfo); two FastAPI annotations in one Annotated raise instead of merging.
**Probe:** `tests/test_ambiguous_params.py` (raises on conflicting annotations) and `tests/test_infer_param_optionality.py` (same param sometimes path/sometimes optional — the reason the path-default check lives in inference, not a hard assert).
