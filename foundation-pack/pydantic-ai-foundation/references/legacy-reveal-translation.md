<!-- capsule-v2 -->
# Legacy fabricated-search translation — upgrading history onto a native reveal channel without rewriting genuine searches

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you recognize old framework-FABRICATED `search_tools` exchanges in stored history and convert them to availability deltas — while never touching searches the model actually made?

## `Model._translate_legacy_tool_reveals` + `_legacy_fabricated_tool_search_reveals` + `_replace_tool_search_exchanges_with_deltas`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/__init__.py:_translate_legacy_tool_reveals` (:785–813), `_legacy_fabricated_tool_search_reveals` (:2185–2236), `_load_capability_ids_by_call` (:2239–2254), `_search_return_discovered_names` (:2257–2267), `_replace_tool_search_exchanges_with_deltas` (:2270–2301).
**Signature:** `_translate_legacy_tool_reveals(self, messages, model_request_parameters) -> list[ModelMessage]` (no-op unless params present AND `tool_addition_mode is not None`).
**Data Shape:** Recognition requires ALL THREE signals per candidate exchange: (1) return `tool_call_id` starts with the framework prefix `_utils.TOOL_CALL_ID_PREFIX`; (2) exact adjacency `[ModelRequest(search_return), ModelResponse(search_call), ModelRequest(load_return…)]` with matching call id; (3) discovered names non-empty-subset of the load_capability-resolved capability's CURRENT tools.

### Decisive source
```python
# models/__init__.py:2200-2234 — three-signal recognition, condensed
for index, message in enumerate(messages):
    if index < 2 or not isinstance(message, ModelRequest) or len(message.parts) != 1: continue
    search_return = message.parts[0]
    if not isinstance(search_return, ToolReturnPart) or search_return.tool_name != TOOL_SEARCH_FUNCTION_TOOL_NAME: continue
    if not tool_call_id.startswith(_utils.TOOL_CALL_ID_PREFIX): continue          # signal 1
    # ... adjacency + name/id match vs messages[index-1], load_return vs [index-2]  # signal 2
    capability_id = capability_by_load_call_id.get(load_return.tool_call_id)
    capability_tools = tools_by_capability.get(capability_id) if capability_id is not None else None
    if not capability_tools: continue
    discovered = _search_return_discovered_names(search_return)
    if discovered is None: continue
    if discovered and set(discovered) <= capability_tools:                        # signal 3
        recognized[tool_call_id] = discovered
```

**Flow:** map load_capability call ids → capability ids (args parsed STRICTLY via `raise_if_invalid=True`) → recognize fabricated exchanges → replace: drop the synthetic call part from its response, rewrite the return into a `ToolAvailabilityDeltaPart(tools_added=discovered)` in place. Genuine exchanges — native or local, ANY provider — are never rewritten: a real search is evidence of what the model did.

**Invariant:** Translation changes only the OUTGOING copy; stored history stays byte-stable (the channel-less path replays unchanged parts verbatim — "byte-identical" is itself pinned). Deciding on the adapter's effective mode alone avoids resolving native tools here, which would preempt `prepare_request`'s more specific unsupported-tool errors. Malformed shapes (bad args JSON, missing metadata, wrong part counts) fail CLOSED to leave-genuine.

**Probe:** `tests/test_tool_availability_portability.py::test_legacy_fabricated_search_translation_matrix` (:593), `..._identity_path_is_byte_identical` (:613), `..._is_left_genuine_without_all_recognizer_conditions` (:627), `..._is_left_genuine_on_malformed_shapes` (:667), `..._upgrades_to_responses_additional_tools` (:1520).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_translate_legacy_tool_reveals _legacy_fabricated_tool_search_reveals _replace_tool_search_exchanges_with_deltas", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the all-three-signals recognition gate (prefix + adjacency + subset-of-current-tools) and the fail-closed-to-genuine posture whenever migrating stored histories onto newer wire channels. Adapt signal specifics to your own fabrication fingerprint. Omit the provider-specific beta-header assertions (Anthropic render twin tested separately at :699).
