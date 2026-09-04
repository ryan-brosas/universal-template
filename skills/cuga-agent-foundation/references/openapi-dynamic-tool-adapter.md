<!-- capsule-v2 -->
# OpenAPI→dynamic-tool adapter — why build pydantic models at runtime, and why do parameters beat body fields on collision?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Given an arbitrary OpenAPI spec, how do you turn each operation into a typed, LLM-callable tool — including URL construction, body/query routing, and error shapes the model can read?

## Runtime model building + param-first collision + never-throwing handler
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/adapter.py` — sanitizer :27-32; naming strategy `determine_operation_name_strategy` :58-106 (settings-clamped `path_segment_index` 1..3, unique-segments check :96); dynamic model factory `build_model` :127-154 (recursive nested-dict specs via `_titleize`, `(type, default)` leaf tuples); optional-field spec `_optional_field_spec` :169-173 (`required → (py_t, ...)` else `(Optional[py_t], None)`); union normalizer `_normalize_union` :185-236 (OpenAPI 3.1 `type: [T,"null"]` list form :195-199; anyOf/oneOf null-filtering; allOf MERGE with first-wins type/items/enum carry :212-234); field walker `_walk_schema_fields` :257-353 (multi-variant anyOf→`Any` leaf :277-286; map-like objects→`Dict[str, T]` :329-337); assembler `new_mcp_from_custom_parser` :680-718 (doc gates `'No-API-Docs'/'Private-API'/'constant' not in path/description` :692-698); handler `create_handler` :604-677.
**Signature:** `handler(params: model, headers: dict = None)` — `params.model_dump()` → route into path/query/body buckets → `construct_final_url` (path `{k}` substitution + list-aware repeated query params :476-499) → `requests.request(json=… if application/json else data=…)`.
**Data Shape:** Field defs: `dict[name -> (python_type, default)] | dict[name -> nested_dict]`; FastMCP validates incoming args against the built pydantic model before the handler runs.

### Decisive source
```python
# adapter.py:420-434 — parameter-vs-body collision policy inside extract_field_definitions
# Check for name collisions between parameters and request body fields
# Parameters (query/path) take precedence over request body fields to avoid conflicts
for key, value in out.items():
    if key not in field_defs:
        field_defs[key] = value
    else:
        logger.warning(f"Name collision in API '{api.operation_id}': field '{key}' exists as both "
                       f"parameter and request body field. Parameter definition (likely query/path) "
                       f"will be used. ...")
```
```python
# adapter.py:652-675 — handlers NEVER raise; errors are DATA for the model
except Exception as e:
    error_response = {"status": "exception", "error_type": type(e).__name__, "message": str(e)}
    if hasattr(e, 'response') and e.response is not None:
        error_response["status_code"] = e.response.status_code
        error_response["url"] = final_url if 'final_url' in locals() else None   # ← may not exist yet
        # append response body text to message so the model sees WHY it failed
```
The `'final_url' in locals()` guard exists because the URL can fail to build BEFORE assignment (bad path params) — a porter who "cleans this up" to reference `final_url` directly introduces a NameError inside the error path itself.

**Flow:** parse spec once → per operation: choose name (unique first-path-segment strategy, else operationId) → collect field defs (parameters + walked body schema) → `build_model` makes `<tool>Input` pydantic class → closure-handler captures api+model+base_url+service-config → register on a per-service FastMCP instance → at call time auth is applied from service config (`apply_authentication` :558-601), `_tokens` header is popped and re-routed (`file_system_access_token` → query/body per override metadata :620-630).
**Invariant:** Optional fields MUST be `Optional[T] = None` or explicit `None` args fail pydantic v2 validation. Handlers return strings-or-error-dicts, never raise — tool exceptions reaching the LLM as stack traces poison trajectories. The doc-gate filter (`No-API-Docs`, `Private-API`) is how upstream marks operations that must NOT become tools.
**Probe:** direct tests `mcp_manager/tests/test_api_response.py` (mocked-request matrix: 404/422-missing-required/connection/timeout/500/400-with-details/successful POST-json/pydantic-validation-in-handler :147-482); naming strategy e2e `registry/test_naming_strategy_e2e.py` (non-unique segments fall back to operationId). Coverage caveat: allOf-merge branch (:212-234) has no dedicated test.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "new_mcp_from_custom_parser extract_field_definitions _normalize_union build_model create_handler", limit: 10 });`

## Verdict
Adopt runtime pydantic model construction from OpenAPI schemas, parameter-over-body collision precedence, the never-raise error-dict funnel, and list-aware repeated-query URL building. Adapt the naming strategy clamp to your settings surface. Omit the `_tokens` re-routing unless you have cross-boundary token injection.
