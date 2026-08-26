<!-- capsule-v2 -->
# MCP sampling model — client-callback Model and the mcp_-prefixed settings namespace

## Source / Question
`pydantic_ai_slim/pydantic_ai/models/mcp_sampling.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** An MCP server asks YOUR client to run a model turn (sampling callback) — how do you expose that as a pydantic-ai Model, and what namespace rule lets its settings merge with any other model's settings dict? A porter will invent unprefixed settings keys that collide during merges.

## Path / Symbol
`models/mcp_sampling.py` — `MCPSamplingModelSettings(ModelSettings, total=False)` (:16–22), `MCPSamplingModel(Model)` (:25–103).

## Signature
```python
class MCPSamplingModelSettings(ModelSettings, total=False):
    """ALL FIELDS MUST BE `mcp_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS."""
    mcp_model_preferences: ModelPreferences

@dataclass
class MCPSamplingModel(Model):
    session: ServerSession          # the MCP server session calling back
    default_max_tokens: int = 16_384
```

## Data Shape
Request path maps pydantic-ai messages → MCP sampling params (`_mcp.map_from_pai_messages`), pulls `max_tokens` (falling back to `default_max_tokens` because sampling REQUIRES it while ModelSettings doesn't guarantee it), `temperature`, `stop_sequences`, `mcp_model_preferences` off the merged settings. Response: only `role == 'assistant'` is a valid outcome; anything else raises `UnexpectedModelBehavior` naming the actual role.

### Decisive source (:48–66)
```python
result = await self.session.create_message(
    sampling_messages,
    max_tokens=model_settings.get('max_tokens', self.default_max_tokens),
    system_prompt=system_prompt,
    temperature=model_settings.get('temperature'),
    model_preferences=model_settings.get('mcp_model_preferences'),
    stop_sequences=model_settings.get('stop_sequences'),
)
if result.role == 'assistant':
    return ModelResponse(parts=[_mcp.map_from_sampling_content(result.content)],
                         model_name=result.model)
else:
    raise exceptions.UnexpectedModelBehavior(
        f'Unexpected result from MCP sampling, expected "assistant" role, got {result.role}.')
```

**Flow:** agent run inside an MCP tool call hits this "model" → messages mapped to sampling format → session.create_message round-trips to the MCP CLIENT's configured LLM → assistant responses map back to ModelResponse; streaming is unsupported by protocol (`request_stream` raises NotImplementedError with the unreachable `yield` keeping it a generator). Identity: `model_name='mcp-sampling'` (unknown until request time), `system='MCP'`, `provider=None`.

**Invariant:** Vendor-specific settings keys MUST be namespaced (`mcp_`) so settings dicts from multiple models merge without collision. Non-assistant sampling outcomes are loud failures, never empty responses. The max_tokens fallback exists because a required provider param sits on an optional settings type.

**Probe:** `tests/test_mcp.py` exercises MCP surfaces (`MCP_SDK_V2` gate :102); sampling covered indirectly via server tests (`tests/mcp_server.py`, `tests/mcp_task_server.py` fixtures). Coverage caveat: no dedicated sampling unit file; behavior pinned through integration paths.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'MCPSamplingModel create_message mcp_model_preferences'
```

## Verdict
**Adopt** the prefixed-settings-merge rule for ANY pluggable model backend. **Adopt** loud non-assistant-role failure. **Adapt** message mapping to your wire format. **Omit** `_mcp.py` mapping internals beyond what this contract needs.
