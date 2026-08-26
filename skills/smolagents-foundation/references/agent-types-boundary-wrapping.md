<!-- capsule-v2 -->
# AgentType wrapping — how do images and audio flow through tool boundaries without breaking str()?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** How does the library pass rich outputs (PIL images, tensors) through LLM-visible strings and back into tools, and which conversion happens at which boundary?

## Dual-face value objects
**Path/Symbol:** `src/smolagents/agent_types.py` — `AgentType` (:32-59), `AgentImage` (:74-173), `AgentAudio/AgentText` (:62-71, :176-251), boundary pair `handle_agent_input_types` (:257-260) / `handle_agent_output_types` (:263-281), mapping `_AGENT_TYPE_MAPPING` (:254).
**Signature:** `AgentImage(value: PIL.Image|bytes|str|Path|Tensor|ndarray)`; `to_raw() -> PIL.Image.Image`; `to_string() -> path:str`; `handle_agent_output_types(output, output_type=None)`; `Tool.__call__(sanitize_inputs_outputs=True)` triggers both.
**Data Shape:** Lazy tri-field `_raw/_path/_tensor`; `to_string()` materializes a temp PNG (`tempfile.mkdtemp()/uuid4.png`) exactly once, caching `_path`.

### Decisive source
```python
# :263-281 — declared output_type wins; else infer from runtime type:
if output_type in _AGENT_TYPE_MAPPING:
    return _AGENT_TYPE_MAPPING[output_type](output)
if isinstance(output, str):        return AgentText(output)
if isinstance(output, PIL.Image.Image): return AgentImage(output)
# tensor → AgentAudio fallback (torch optional)
```

**Flow:** Tool returns a PIL image → `handle_agent_output_types` wraps as AgentImage → stored in `agent.state["image.png"]` (agents.py:1392-1399) with observation text "Stored 'image.png' in memory." so the model sees a NAME, not pixels → next code action references `image.png`, `execute_tool_call`'s state-variable substitution dereferences it → at the tool boundary `handle_agent_input_types` calls `.to_raw()` giving the callee a real PIL image. Because AgentText subclasses `str` and AgentImage subclasses `PIL.Image.Image`, un-wrapped consumers still work by inheritance. Tensor→image path inverts channels `(255 - array*255)` — a documented quirk of the normalized-tensor convention.
**Invariant:** Wrapping is boundary-scoped, not global: memory observations intentionally carry the stringified form (token-cheap), while raw objects travel only through agent state into typed tool parameters. Porters who stringify eagerly lose image passing; porters who skip sanitization crash forward() with wrapper objects.
**Probe:** `tests/test_types.py` (wrapping matrix incl. tensor paths) + `tests/test_agents.py::test_toolcalling_agent_handles_image_tool_outputs/_inputs` (:427-465). Live: wrap a 2×2 PIL image → to_string() ends .png; to_raw() returns PIL instance.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "AgentImage handle_agent_input_types handle_agent_output_types", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt boundary-scoped wrapping keyed on declared output_type first, runtime type second. Adapt the temp-file materialization (path-based handoff assumes a shared filesystem — remote hosts serialize instead). Omit the channel-inversion quirk only if you also own the tensor convention.
