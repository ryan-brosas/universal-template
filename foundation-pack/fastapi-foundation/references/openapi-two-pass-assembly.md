<!-- capsule-v2 -->
# get_openapi two-pass schema assembly — How are definitions collected once and reused across all operations, and how do 422s, streaming schemas, and openapi_extra merge?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** What is the pass structure of OpenAPI generation, and which rules decide when the automatic 422 response appears?

## Pass 1 collect fields → Pass 2 render operations
**Path/Symbol:** `fastapi/openapi/utils.py:get_openapi` (585–679) + `get_fields_from_routes` (551–582) + `get_openapi_path` (311–540) + `_get_openapi_dependency_data` (99–129).
**Signature:** `get_openapi(*, title, version, routes, webhooks=None, separate_input_output_schemas=True, ...) -> dict`; `get_fields_from_routes(routes) -> list[ModelField]`.
**Data Shape:** pass 1 walks `iter_route_contexts` (so lazily-included routers contribute their EFFECTIVE paths) collecting body_field, response_field, response_fields, stream_item_field, callbacks (recursive), and `get_flat_params(dependant)`; pass 2 renders each operation against a single `model_name_map`/`field_mapping` so every `$ref` resolves to one shared `components/schemas`.

### Decisive source
```python
    all_fields = get_fields_from_routes(list(routes) + list(webhooks or []))
    flat_models = get_flat_models_from_fields(all_fields, known_models=set())
    model_name_map = get_model_name_map(flat_models)
    field_mapping, definitions = get_definitions(fields=all_fields, model_name_map=model_name_map,
                                                 separate_input_output_schemas=separate_input_output_schemas)
```
422 gate:
```python
            http422 = "422"
            if (all_route_params or route.body_field) and not any(
                status in operation["responses"] for status in [http422, "4XX", "default"]):
                operation["responses"][http422] = {... "$ref": REF_PREFIX + "HTTPValidationError"}
                if "ValidationError" not in definitions:
                    definitions.update({"ValidationError": validation_error_definition,
                                        "HTTPValidationError": validation_error_response_definition})
```

**Flow:** security extraction walks the dependant tree with cache-key dedupe, collecting ONLY non-root SecurityBase dependants plus their inherited scopes; same-scheme scopes MERGE into one `{scheme: [scopes]}` operation entry → parameters deduped by `(in, name)` with REQUIRED definitions overriding non-required duplicates → status code falls back to inspecting the response class `__init__` default → JSONL responses document `itemSchema` per item; SSE documents `_SSE_EVENT_SCHEMA` with `data.contentSchema` = the stream item's schema → additional `responses={...}` models deep-merge (`deep_dict_update`, lists CONCATENATE) with descriptions resolved from http.client → `route.openapi_extra` merged LAST over the whole operation.
**Invariant:** (1) The 422 auto-response appears only when params/body exist AND the user hasn't declared 422, "4XX", or "default" — declaring a range suppresses it. (2) Definitions output is sorted by name for deterministic diffs. (3) The final document re-encodes through `jsonable_encoder(OpenAPI(**output), by_alias=True, exclude_none=True)` — the pydantic model validates/coerces the assembled dict.
**Probe:** `tests/test_openapi_route_extensions.py` + the tutorial-pinned openapi snapshot suites (e.g. `docs_src`-backed `test_tutorial/test_extra_models*`) pin refs, 422 suppression, and webhook sections.
