<!-- capsule-v2 -->
# Weak-schema sentinel — how do you detect "tool has no declared output schema" when the fallback placeholder is byte-identical to a real string schema?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How can prompt-side code know an MCP tool's `success: {"type": "string"}` is a synthetic placeholder rather than the tool's real declared output?

## Marker-tagged placeholder across mcp_manager → prompt_utils
**Path/Symbol:** producer `src/cuga/backend/tools_env/registry/mcp_manager/mcp_manager.py:660-664`; consumer `src/cuga/backend/cuga_graph/nodes/cuga_lite/prompt_utils.py:20-33,277-298` (`is_weak_schema_tool`, `_SYNTHETIC_PLACEHOLDER_KEY`), directive `_WEAK_SCHEMA_PROBE_DIRECTIVE` :20-25.
**Signature:** `is_weak_schema_tool(tool: StructuredTool) -> bool` — reads `tool.func._response_schemas`.
**Data Shape:** `_response_schemas: dict` with `success`/`failure` keys; the sentinel is a literal `"​_synthetic_placeholder": True` entry injected ONLY when the tool declared no `outputSchema`. Kept in sync as plain literals in both files to avoid a graph→registry import dependency.

### Decisive source
```python
# mcp_manager.py:658-664 — tag at PRODUCTION time
api_info["response_schemas"] = {
    "success": {"type": "string"},
    "failure": {"type": "string"},
    "_synthetic_placeholder": True,
}
```
```python
# prompt_utils.py:288-298 — trust the MARKER, never match on shape
# A genuine string-returning tool (an OpenAPI text/plain body, or an MCP
# tool that actually declares ``outputSchema: {"type": "string"}``) produces
# a ``success`` schema *identical* to that placeholder ... so we no longer
# match on shape ... and we trust that marker.
if not response_schemas or not isinstance(response_schemas, dict):
    return True
return bool(response_schemas.get(_SYNTHETIC_PLACEHOLDER_KEY))
```

**Flow:** manager builds tool metadata; no declared outputSchema ⇒ synthesize success/failure string schemas AND stamp the sentinel key → registry serves them → prompt-side `get_tool_docs` asks `is_weak_schema_tool`: missing/empty schemas ⇒ weak; sentinel present ⇒ weak; anything else ⇒ real schema rendered verbatim. Weak tools get `_WEAK_SCHEMA_PROBE_DIRECTIVE` appended ("Call it ALONE in its own ```python block and print() the raw result") instead of a fabricated schema.
**Invariant:** shape-matching suppressed REAL schemas before this design (a genuine text/plain OpenAPI body was mis-flagged weak); detection must be marker-based because the wire format cannot distinguish the two cases; the directive exists so the model treats unknown-shape outputs as data to observe, not structure to index into. This contract pairs with code-extraction's probing-tool isolation (weak tools run alone in their own turn).
**Probe:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_prompt_utils_weak_schema.py` pins all four quadrants: empty-dict→weak (:15), attr-missing→weak (:20), sentinel→weak (:25), real-object-schema→not-weak (:37), plus the two regressions — bare-string success WITHOUT marker must render as a real schema (:44-50, :72-78) and sentinel-bearing gets the probing directive (:60-69).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "is_weak_schema_tool _synthetic_placeholder response_schemas", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the produce-side-stamps / consume-side-trusts-marker pattern for ANY cross-boundary "is this synthesized?" question where synthesized and genuine payloads are indistinguishable on the wire; adapt the key name and directive copy; omit the OpenAPI empty-response_schemas branch if your tools always declare outputs. Direct tests pin both regressions that motivated the marker.
