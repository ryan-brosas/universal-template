<!-- capsule-v2 -->
# Schema include/override pre-processor — why mutate a COPY of the spec, and why must dropped `$ref` body params inline the resolved schema?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Before an OpenAPI spec becomes tools, operators need to hide operations and delete toxic parameters (internal flags, debug knobs) — how do you rewrite the spec safely so generated tools never see them?

## Filter-then-override pass with recursive parameter excision
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/mcp_manager.py` — `_filter_and_override_schema(schema_data, config)` :252-399 (early-return when neither `include` nor `api_overrides`; shallow copy; operation filter keeps ONLY methods get/post/put/delete/patch/head/options with matching operationId while PRESERVING non-operation path items :277-284); `_remove_parameter_from_body_schema` :209-248 (copy properties, drop from `required` too, recurse into allOf/anyOf/oneOf lists); `$ref` resolution at :334-367 (navigate `#/components/schemas/...` segments, MISSING segment → abort modification for that ref, not crash); re-parse gate in `initialize_servers` :1295-1309 (parser rebuilt from yaml.dump of modified schema only when include or ANY override present).
**Signature:** `_remove_parameter_from_body_schema(body_schema, parameter_name) -> modified_copy`.
**Data Shape:** Config inputs: `include: [operationId...]`, `api_overrides: [{operation_id, description?, drop_request_body_parameters?, drop_query_parameters?}]`.

### Decisive source
```python
# mcp_manager.py:334-337 + 352-367 — dropping a param from a $ref'd body requires
# INLINING the modified schema (you cannot mutate the shared component safely)
if '$ref' in schema_ref:
    ref_path = schema_ref['$ref']
    if ref_path.startswith('#/'):
        resolved_schema = modified_schema
        for part in ref_parts:
            if part in resolved_schema:
                resolved_schema = resolved_schema[part]
            else:
                resolved_schema = None   # ← unresolvable: SKIP, don't raise
                break
        if resolved_schema:
            modified_body_schema = resolved_schema.copy()
            for param_to_drop in body_override_map[operation_id]:
                modified_body_schema = self._remove_parameter_from_body_schema(...)
            content_schema['schema'] = modified_body_schema   # ← $ref REPLACED by inline dict
```
Why inline instead of editing the component: multiple operations share `#/components/schemas/UserRequest`; mutating it would leak the deletion into every OTHER operation that references it. Inlining scopes the change to exactly one request body.
```python
# mcp_manager.py:235-237 — dropping a property without fixing `required` breaks validation
if 'required' in modified_schema and isinstance(modified_schema['required'], list):
    required = [req for req in modified_schema['required'] if req != parameter_name]
    modified_schema['required'] = required
```
**Flow:** fetch raw spec → `_filter_and_override_schema` → store as `schemas[name]` → IF any filtering happened, rebuild the parser from the serialized modified spec (the parser instance from initial fetch is stale) → build FastMCP server whose handlers consult `get_operation_override_parameters` at CALL time to route injected tokens into the slots where dropped params used to live.
**Invariant:** Never mutate the input spec — every branch works on copies (shallow copy at top, per-schema copies before recursion). Unresolvable refs degrade to no-op, never KeyError. The include filter must keep non-operation keys (`parameters`, `summary`) on surviving paths or the filtered spec stops being valid OpenAPI. A dropped parameter must ALSO leave the `required` list or pydantic model generation will demand it.
**Probe:** direct tests `registry/tests/test_output_schema.py` (843L suite over response-schema extraction incl. overridden ops) and `mcp_manager/tests/test_api_response.py` handler matrix; override routing covered via adapter tests. Coverage caveat: the allOf/anyOf recursion inside param removal (:240-246) lacks a dedicated test — verify by reading :209-248.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_filter_and_override_schema _remove_parameter_from_body_schema api_overrides include", limit: 10 });`

## Verdict
Adopt copy-only spec rewriting, scoped inline replacement of shared refs, required-list synchronization, and the stale-parser rebuild gate. Adapt to your config vocabulary. Omit composition recursion if your specs are flat.
