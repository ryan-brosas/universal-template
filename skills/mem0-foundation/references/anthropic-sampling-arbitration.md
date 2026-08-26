<!-- capsule-v2 -->
# Anthropic sampling arbitration — how do you never send temperature+top_p together and still salvage text when thinking blocks precede it?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** which of temperature/top_p is sent when both are configured (per model family), how is that gate versioned per Claude model, and what does response parsing owe to extended-thinking responses?

## Connected graph-selected seam
**Path/Symbol:** `mem0/llms/anthropic.py`: `_enable_sampling_parameters` (:47-69), `_get_common_params` (:71-95), system-message extraction (:118-125), `_parse_response` (:143-159). Direct tests `tests/llms/test_anthropic.py`: `test_default_config_omits_top_p` (:20), `test_generate_response_does_not_send_top_p_by_default` (:27), `test_generate_response_sends_top_p_alone_when_no_temperature` (:48), `test_both_set_prefers_temperature_over_top_p` (:69), `test_enable_sampling_parameters_for_current_models` (:154 parametrized matrix), `test_generate_response_returns_text_when_thinking_block_precedes_it` (:169), `test_generate_response_returns_empty_string_on_empty_content` (:189).
**Signature:** `_enable_sampling_parameters() -> bool`; `_get_common_params(**kwargs) -> Dict` (override of the base-class common params); `_parse_response(response, tools) -> str | {"content", "tool_calls"}`.
**Data Shape:** model-name grammar parsed as `family[-major[-minor]]` after stripping a `[...]` suffix (`rsplit("[",1)[0].split("-")`); gates: haiku → always; sonnet → major<5; opus → (major,minor)<(4,7); anything unversioned/unrecognized → False.

### Decisive source
```python
def _get_common_params(self, **kwargs) -> Dict:
    """Anthropic rejects requests that include both temperature and top_p.
    When both are set, we keep temperature and drop top_p."""
    params = {}
    if self.config.max_tokens is not None:
        params["max_tokens"] = self.config.max_tokens
    has_temperature = self.config.temperature is not None
    has_top_p = self.config.top_p is not None
    if self._enable_sampling_parameters():
        if has_temperature and has_top_p:
            params["temperature"] = self.config.temperature      # BOTH set ⇒ temperature wins
        elif has_temperature:
            params["temperature"] = self.config.temperature
        elif has_top_p:
            params["top_p"] = self.config.top_p                  # top_p ONLY when no temperature
    params.update(kwargs)
    return params

# thinking-enabled responses: a thinking block precedes text, or there is NO text block at all
for block in response.content:            # ← scan, never content[0]
    if block.type == "text":
        return block.text
return ""                                  # empty-content responses degrade to "", not IndexError
```

**Flow:** ctor fills default model `claude-sonnet-4-6`, resolves api_key/base_url (base_url omitted entirely when unset — test-pinned) → `generate_response` splits system out of messages into the top-level `system=` arg → params assembled via `_get_supported_params` (reasoning-model gate inherited from llms/base) then updated with model/messages/system → tools become `tool_choice={"type": tool_choice}` (object-wrapped, not bare string) → response scanned block-by-block for text/tool_use.
**Invariant:** (1) both-set ⇒ temperature wins and top_p is dropped SILENTLY — surfacing an error here would break every legacy config that sets both; (2) the whole sampling pair is gated by `_enable_sampling_parameters()` — newer models than the gate knows get NEITHER parameter (safe default: omit rather than guess); (3) explicit `enable_sampling_parameters` config beats the family heuristic; (4) text extraction must SCAN blocks (thinking-first layouts put text at index ≥1; some responses carry zero text blocks) — `content[0]` indexing is the classic porting bug; (5) default config omits top_p entirely so first-run requests are single-knob.
**Probe:** `tests/llms/test_anthropic.py::test_both_set_prefers_temperature_over_top_p`, `::test_generate_response_sends_top_p_alone_when_no_temperature`, `::test_default_config_omits_top_p`, `::test_generate_response_returns_text_when_thinking_block_precedes_it`, `::test_generate_response_returns_empty_string_on_empty_content`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_enable_sampling_parameters AnthropicLLM _get_common_params thinking block", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the prefer-temperature arbitration and the block-scan parser verbatim — both encode provider hard-failures turned silent; adapt the family/major/minor version gates as new Claude lines ship (keep explicit-override precedence and the unknown→omit fallback); omit the vision/vision_details plumbing if your port never sends images.
