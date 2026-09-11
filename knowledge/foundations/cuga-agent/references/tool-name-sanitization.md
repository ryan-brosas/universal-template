<!-- capsule-v2 -->
# Tool-name sanitization + collision guard — why does `echo-with-dash` become a valid Python identifier, and why must the FIRST colliding tool win?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** MCP tool names arrive with dashes, dots, spaces — generated code calls them as functions. How do you make every name safe WITHOUT losing the original, and what breaks when two names sanitize identically?

## Sanitize-to-identifier + reverse map + first-wins collision skip
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/adapter.py:27-32` (`sanitize_tool_name`); registration loop + guard `src/cuga/backend/tools_env/registry/mcp_manager/mcp_manager.py:784-818` (collision check :793-800, reverse-map write :803); reverse lookup on call `_call_mcp_server_tool` :1143; stale cleanup `_clear_mcp_server_registration` :686-696 (pops BOTH maps).
**Signature:** `sanitize_tool_name(name) -> str`: lowercase → `re.sub(r'[ /.\-{}:?&=%]', '_', s)` → collapse runs `__+→_` → strip leading/trailing `_` → fallback literal `"unnamed_tool"` if empty. Registration: `prefixed_name = f"{server}_{sanitized}"`.
**Data Shape:** Two parallel dicts kept in lockstep: `server_by_tool: {prefixed_sanitized_name -> server}` (dispatch key) and `original_tool_name_by_sanitized: {prefixed_name -> ORIGINAL server-side name}` (wire name). The MCP server only ever knows the ORIGINAL dashed name; the LLM only ever sees the SANITIZED prefixed one.

### Decisive source
```python
# mcp_manager.py:790-803 — the guard that makes sanitization lossless-but-unique
# Detect sanitization collisions: two tools on the same server whose
# names differ only by dash vs underscore would map to the same
# prefixed_name, making the reverse lookup ambiguous.
if prefixed_name in self.original_tool_name_by_sanitized:
    existing_original = self.original_tool_name_by_sanitized[prefixed_name]
    logger.warning(f"... Skipping '{tool.name}' to avoid overwriting the existing mapping.")
    continue                                   # ← FIRST registration wins; second is SKIPPED
self.original_tool_name_by_sanitized[prefixed_name] = tool.name
```
Why first-wins-skip rather than error or rename: the registry must stay deterministic across reconnects (a rename-on-collision scheme could reorder which tool gets suffix `_2` between boots), silently dropping ONE ambiguous tool beats nondeterministically swapping two. The test suite mirrors this exact loop because it's the contract.

**Flow:** server connects → for each tool: sanitize → prefix with server name → collision? skip+warn : register in both maps → LLM binds `{prefix}_{tool}` → on call, `_call_mcp_server_tool` sends `original_tool_name_by_sanitized[tool_name]` back over the wire (:1141-1149). OpenAPI path shares the convention from the other side: `_get_response_schema_from_tool` strips `len(prefix)+1` chars to recover the operationId (:152-162) — so ANY change to the sanitizer breaks response-schema recovery too.
**Invariant:** Registered names MUST be valid Python identifiers (`isidentifier()`) — generated code does `result = {name}(...)` and compiles it. The reverse map is not optional bookkeeping: without it, calling a dashed tool sends the sanitized name the server doesn't know. Cleanup must pop from both maps together or stale entries resurrect ghost tools after a reconnect.
**Probe:** direct tests `src/cuga/backend/tools_env/registry/mcp_manager/tests/test_dashed_tool_names.py` — issue #185 regression: `test_dashed_tool_registered_as_valid_identifier` :90, `test_dashed_tool_name_compiles` :114 (compiles generated code!), `test_reverse_map_dashed_tool` :103, sanitizer parametrize `test_sanitize` :136-149, `test_clear_removes_reverse_map_entries` :122, collision pair :184/:189.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "sanitize_tool_name original_tool_name_by_sanitized server_by_tool", limit: 10 });`

## Verdict
Adopt sanitize-to-identifier with server-prefix namespacing, the parallel original-name reverse map, first-registration-wins collision skipping, and lockstep cleanup. Adapt the character class to your language's identifier rules. Omit the `"unnamed_tool"` fallback only if upstream guarantees non-empty names.
