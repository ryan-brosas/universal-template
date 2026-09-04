<!-- capsule-v2 -->
# Tool-availability delta dual render — mechanism or news? How one recorded part projects onto providers that can (and can't) withhold schemas

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A `ToolAvailabilityDeltaPart` sits in history saying "these tools now exist" — how is it rendered for a model whose API can withhold a schema vs one that can't, without fabricating actions or colliding call ids?

## `Model.prepare_messages` fork → `_synthesize_tool_availability_delta_messages` / `_announce_tool_availability_delta_messages`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/__init__.py:prepare_messages` (:690–783), `_hides_deferred_schemas` (:815–829), `_synthesize_tool_availability_delta_messages` (:2364–2455), `_announce_tool_availability_delta_messages` (:2304–2361), `TOOL_AVAILABILITY_ANNOUNCEMENT` (:2174–2182).
**Signature:** `prepare_messages(messages: list[ModelMessage], model_request_parameters: ModelRequestParameters | None = None) -> list[ModelMessage]`; synthesizer takes `(messages, available_tool_names: set[str] | None)`.
**Data Shape:** `available_tool_names = {tool.name for tool in params.function_tools if tool.defer_loading}` when params passed; `None` means "no definitions to validate against, render as recorded" (bare direct-call form). Synthesized ids: `{TOOL_CALL_ID_PREFIX}{blake2s(ordinal + names)[:8]}`, ordinal stable across requests because history is append-only.

### Decisive source
```python
# models/__init__.py:770-773 — the fork
if self._hides_deferred_schemas(model_request_parameters):
    messages = _synthesize_tool_availability_delta_messages(messages, available_tool_names)
else:
    messages = _announce_tool_availability_delta_messages(messages, available_tool_names)

# :2439-2438 — collision-proof synthetic id seeded with ids already in history
history_call_ids = {part.tool_call_id for message in messages for part in message.parts
                    if isinstance(part, BaseToolCallPart | BaseToolReturnPart | RetryPromptPart)}
# ... if tool_call_id is None or in synthesized_ids or in history_call_ids:
#     while True: digest = blake2s('\x00'.join([str(synthesized_count), *added])...
```

**Flow:** collect delta parts → if none or tool-addition supported natively, skip → else decide by `_hides_deferred_schemas` (any resolved visibility == 'deferred'): CAN-withhold → synthesize a local `search_tools` exchange per delta — the return IS the unhide mechanism (Anthropic renders it as the `tool_reference` block); CANNOT → replace each delta in place with a mid-conversation `SystemPromptPart` stating only `'The following tool(s) are now available: ...'` (later degraded to `<system>`-tagged user text by `_wrap_non_leading_system_prompts`). Empty adds drop silently; a request left partless is dropped.

**Invariant:** The old fabrication was wrong three ways and all three stay dead: it attributed a search to the model (mixed-corpus cause confusion), could name an undeclared `search_tools` tool (providers reject), and minted duplicate tool_call_ids across deltas over the same names (uniqueness-rejecting providers choke). Hence: announcement states ONLY the fact (the tools are already visible in the request's tools list; naming them suffices), synthesis seeds uniqueness against ALL history ids AND previously synthesized ones, and the split-at-delta-position preserves conversation order (emitting everything after the synthetic response would hoist an assistant turn ahead of a preceding user prompt).

**Probe:** `tests/test_tool_availability_portability.py::test_mixed_corpus_reveal_gets_the_mechanism_not_just_the_news` (:1243), `test_delta_reusing_a_live_call_id_gets_a_fresh_synthesized_id` (:1322), `test_delta_reusing_a_collapsed_exchange_id_passes_it_through` (:1357), `test_fabricated_id_skips_a_client_authored_lookalike` (:1372), `test_unrenderable_delta_raises_user_error_not_assertion` (:1225), plus the cache-prefix stability pins (:1038, :1143).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_synthesize_tool_availability_delta_messages _announce_tool_availability_delta_messages TOOL_AVAILABILITY_ANNOUNCEMENT _hides_deferred_schemas", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-job fork keyed on schema-withholding ability, the fact-only announcement wording, and the collision-seeded id minting with stable ordinals. Adapt the native render channel (tool_addition blocks vs prose) per provider. Omit nothing — the id-collision and turn-order traps are the real content.
