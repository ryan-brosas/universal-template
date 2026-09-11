<!-- capsule-v2 -->
# Body embed decision + Body_ composite model — When is the JSON body the whole payload vs a dict of named fields?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** What decides `embed_body_fields`, and how are multiple body params (possibly across dependency boundaries) merged into one synthetic `Body_<op>` model for schema and media-type purposes?

## Embed rule and body synthesis
**Path/Symbol:** `fastapi/dependencies/utils.py:_should_embed_body_fields` (888–909) + `_get_body_field` (1001–1049) + `request_body_to_args` (951–998); called per route from `fastapi/routing.py:_build_dependant_with_parameterless_dependencies` (855–869) / `_populate_api_route_state` (1066–1070).
**Signature:** `_should_embed_body_fields(fields: list[ModelField]) -> bool`; `_get_body_field(*, body_params, name, embed_body_fields) -> ModelField | None`.
**Data Shape:** embed=True when: >1 distinct field NAME, or explicit `.embed`, or a Form/File non-model scalar (must be keyed to be extracted). Note fields are deduped by NAME because several dependencies often declare the same body param.

### Decisive source
```python
def _get_body_field(*, body_params, name, embed_body_fields):
    if not body_params: return None
    first_param = body_params[0]
    if not embed_body_fields:
        return first_param                      # whole-body single model
    BodyModel = create_body_model(fields=body_params, model_name="Body_" + name)
    required = any(f.field_info.is_required() for f in body_params)
    if any(isinstance(f.field_info, params.File) for f in body_params):
        BodyFieldInfo = params.File             # media type follows the "widest" member
    elif any(isinstance(f.field_info, params.Form) for f in body_params):
        BodyFieldInfo = params.Form
    else:
        BodyFieldInfo = params.Body
        media_types = {f.field_info.media_type for f in body_params if isinstance(f.field_info, params.Body)}
        if len(media_types) == 1:               # only when unambiguous
            BodyFieldInfo_kwargs["media_type"] = media_types.pop()
    return create_model_field(name="body", type_=BodyModel, alias="body", field_info=BodyFieldInfo(**kwargs))
```

**Flow:** route build collects flat body params across the WHOLE dependant tree (`_get_flat_body_params`) → embed decided once → runtime `request_body_to_args`: single non-embedded path validates received body directly against `first_field` with loc `("body",)`; embedded path reads each alias out of the dict/FormData (AttributeError on list-shaped bodies becomes a missing-field error); FormData bodies first pass through `_extract_form_body` which also folds undeclared keys and eagerly `read()`s bytes-typed UploadFiles.
**Invariant:** (1) The docstring of `_get_body_field` states it is for SCHEMA/media-type decisions only — actual validation uses individual body params; conflating the two breaks error locs. (2) Mixed File+Form ⇒ multipart; a lone custom media_type survives only when ALL Body members agree. (3) The synthetic model name embeds `route.unique_id` so two operations with same-shaped bodies don't collide in the OpenAPI schema map.
**Probe:** `tests/test_multi_body_errors.py` (embedded multi-body validation errors) and docs-backed suites under `tests/test_body_*` pin both branches' wire shapes.
