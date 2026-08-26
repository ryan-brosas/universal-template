<!-- capsule-v2 -->
# Response-schema extraction with recursive $ref resolution — how do you hand an LLM the exact response shape of an OpenAPI operation across 3.x and Swagger-2 specs?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Given an OpenAPI spec and an operationId, how do you extract the fully-dereferenced response schema (status precedence, content-type precedence, recursion) that tool docs promise the model?

## operationId lookup → status 200→201→first → content application/json → */* → first → resolve refs recursively
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/response_schema.py` — `resolve_ref` :90-120, `resolve_schema_references` :123-174, `extract_response_schema` :177-249 (OpenAPI-3 branch :192-221, Swagger-2 twin :224-247); consumer `mcp_manager.py:34` (`from ...response_schema import extract_response_schema`).
**Signature:** `resolve_ref(ref, openapi_spec) -> dict` (local `#/...` only; external refs print + return {}); `resolve_schema_references(schema, spec) -> dict`; `extract_response_schema(openapi_spec, operation_id) -> dict`.
**Data Shape:** walks `spec['paths'][path][method]`, methods filtered to get/post/put/delete/patch/options/head; matches `operation.get('operationId').lower() == operation_id.lower()` in 3.x but CASE-SENSITIVE raw compare in the Swagger-2 branch.

### Decisive source
```python
# :204-221 — the precedence ladder, then "first response found" fallback
for status_code in ['200', '201']:
    if status_code in responses:
        content = responses[status_code].get('content', {})
        for content_type in ['application/json', '*/*']:
            if content_type in content:
                schema = content[content_type].get('schema', {})
                return resolve_schema_references(schema, openapi_spec)
# no 200/201 ⇒ FIRST entry in responses dict wins (insertion order)
for status_code, response in responses.items(): ...
```
```python
# :148-157 — recursion covers properties / items / allOf-anyOf-oneOf /
# additionalProperties; a resolved $ref ITSELF containing $ref re-resolves (:117)
```
**Flow:** find operation by id → pick schema by status/content ladder → recursively inline `$ref`s (properties, array items, combinators, additionalProperties) → return plain dict. Loaders `load_openapi_spec(file)` / `fetch_openapi_spec(url)` handle .json/.yaml by suffix then Content-Type, defaulting to JSON-with-yaml-fallback; failures print and return `{}`.
**Invariant:** (1) Resolution is INLINE-COPY (schema.copy() + update) — never mutate the spec. (2) External `$ref`s degrade to empty dict with a printed warning — no crash. (3) The 3.x/2.x twins differ ONLY in schema location (`content.{type}.schema` vs `response.schema`) and operationId case-sensitivity — porters must keep both ladders aligned when editing one. (4) Empty result is a valid answer ({}) — callers must treat falsy as "unknown shape", not retry.

**Probe:** No direct unit suite for response_schema.py at HEAD (coverage caveat — pinned indirectly through parser tests `tests/test_enum_handling.py::test_openapi_enum_processing_integration` which exercise the sibling SimpleOpenAPIParser response path this module feeds).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "extract_response_schema resolve_ref resolve_schema_references operationId", limit: 8 });
```
## Verdict
Adopt the two-ladder precedence (status then content-type) plus recursive local-ref resolution for any spec-to-docstring pipeline. Adapt to your spec version support. Omit the Swagger-2 twin if you only ingest 3.x — but keep the case-sensitivity decision consistent.
