<!-- capsule-v2 -->
# OpenAPI v0 transformer — human-readable schema summarization with circular-ref sentinels and example-first shapes

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does the legacy v0 path turn a raw OpenAPI spec into LLM-friendly tool documentation, and which resolution rules differ from the current parser?

## OpenAPITransformer summarizes schemas for prompts, not validation
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/openapi_parser_v0.py` (`OpenAPITransformer.__init__` :13-32, `_resolve_ref` :118-147, `_select_variant` :84-116, `_summarize_param_schema` :34-82, `_extract_parameters` :336-448, `_extract_response_schemas` :450-491, `transform` :523-573).
**Signature:** `OpenAPITransformer(openapi_schema: str|dict, filter_patterns=None)` → `.transform() -> Dict[api_name_key, operation_details]`.
**Data Shape:** output per operation: `{app_name, secure, api_name, operation_id, path, method, description, parameters[], response_schemas{success,failure}, canary_string}`; parameters merge path-level then operation-level by `(name, in)` (operation-level wins), and requestBody object fields explode into individual params using `required[]` from the body schema.

### Decisive source
```python
# openapi_parser_v0.py:122-133 — cycles and external refs become DATA, never loops
while isinstance(current_obj, dict) and '$ref' in current_obj:
    ref_path_str = current_obj['$ref']
    if ref_path_str in visited_refs:
        return {"type": "circular_ref", "ref": ref_path_str,
                "error": "Circular reference detected"}
    visited_refs.add(ref_path_str)
    if not ref_path_str.startswith('#/'):
        return {"type": "unresolved_external_ref", ...}
```
Union selection preference (`_select_variant` :95-115): resolve every anyOf/oneOf/allOf candidate, drop explicit nulls, prefer an object-with-properties variant, else first non-null — and `example` BEATS type everywhere in summaries (:51-52).

**Flow:** app name resolved x-app-name → info.x-app-name → title minus suffixes (" API"/" Service"/" Application") → first tag → `"unknown_app"`; operations filtered when their description contains a filter pattern (defaults `["No-API-Docs", "Private-API"]`, case-insensitive substring); name strategy comes from the SHARED adapter (`determine_operation_name_strategy`), final key = `sanitize_tool_name(f"{app_name}_{api_name}")`; duplicate keys overwrite with a printed warning; response side buckets first 2xx into `success` and first 4xx/5xx/default into `failure`.
**Invariant:** this summarizer must NEVER throw on hostile specs — every degenerate shape degrades to sentinel strings (`"unknown"`, `"object"`, `"circular_ref"`); constraint text (enum/min-max/pattern) is rendered as human strings because its consumers are prompts, NOT validators.
**Probe:** `src/cuga/backend/tools_env/registry/mcp_manager/tests/test_array_handling.py` (:164+ v0 array handling, :233 problematic-schema resilience — the suite header states it covers BOTH SimpleOpenAPIParser and the v0 OpenAPITransformer).
**Retrieve:**
```python
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "OpenAPITransformer transform openapi_parser_v0", limit: 5 });
```

## Verdict
Adopt only when you need prompt-facing schema summarization of untrusted specs (the sentinel-degradation + example-first rules are the reusable part). For wire-accurate parsing use the current parser (`openapi-composition-flattening.md`, `openapi-response-extraction.md`) — v0 differs most visibly in example-beats-type and requestBody field explosion.
