<!-- capsule-v2 -->
# Token counter contract — what does token counting promise, and when does it deliberately answer 0?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `litellm`. **Question:** How are text/messages/tools/images counted, which inputs are mutually exclusive, and where do estimation fallbacks apply?

## `token_counter` + image tokens
**Path/Symbol:** `litellm/litellm_core_utils/token_counter.py:token_counter` (:345-411, fan-in ≈48); `_count_image_tokens` (:582-620); `_fix_model_name` (:571-579).
**Signature:** `def token_counter(model="", custom_tokenizer=None, text=None, messages=None, count_response_tokens=False, tools=None, tool_choice=None, use_default_image_token_count=False, default_token_count=None) -> int`.
**Data Shape:** accepts raw `text` (str | list[str]) XOR `messages`; returns int; never raises on tokenizer failure inside aggregation paths (callers wrap in try/except → 0).

### Decisive source
```python
    if litellm.disable_token_counter is True:
        return 0
    ...
    if text is not None and messages is not None:
        raise ValueError("text and messages cannot both be set")
    ...
    elif messages is not None:
        new_messages = cast(list[AllMessageValues], convert_list_message_to_dict(messages))
        params = _MessageCountParams(model, custom_tokenizer)
        num_tokens = _count_messages(params, new_messages, use_default_image_token_count, default_token_count)
        if count_response_tokens is False:
            includes_system_message = any([message.get("role") == "system" for message in new_messages])
            num_tokens += _count_extra(params.count_function, tools, tool_choice, includes_system_message)
```
(:381-406) — model-name normalization feeding the encoding choice:
```python
def _fix_model_name(model: str) -> str:
    if model in litellm.azure_llms:
        return model.replace("-35", "-3.5")   # azure llms use gpt-35-turbo 🙃
    elif model in litellm.open_ai_chat_completion_models:
        return model
    else:
        return "gpt-3.5-turbo"
```
(:571-579). Image blocks: `_count_image_tokens` validates `detail ∈ {low, high, auto}` and rejects empty URLs before `calculate_img_tokens(data=url, mode=detail, use_default_image_token_count=...)` (:599-618).

**Flow:** kill-switch (`disable_token_counter` → 0) → exclusivity check → text path (join list, no chat overhead, tools forbidden with text :391-392) or messages path (`_count_messages` incl. per-message + image/audio math, then `+ _count_extra` chat-format overhead only when NOT counting response tokens) → int.
**Invariant:** response-token counts (`count_response_tokens=True`) exclude chat-format overhead; unknown models silently fall back to the gpt-3.5-turbo encoding rather than erroring; a CPU-cost kill switch must exist for hosted callers.
**Probe:** executed live at the pin: `token_counter(model="gpt-3.5-turbo", text="hello world")` → 2. Direct tests: `tests/test_litellm/litellm_core_utils/test_token_counter.py`, `test_token_counter_tool.py`, `test_token_counter_tool_data.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm", name_pattern: "token_counter" });
// → token_counter Function :345-411 and _count_image_tokens Function :582-620 in litellm_core_utils/token_counter.py (verified at pin)
```

## Verdict
Adopt: exclusivity of raw-text vs message-list modes, response-vs-request overhead split, graceful 0 via kill switch and caller-side try/except, unknown-model encoding fallback. Adapt the tokenizer registry (tiktoken vs custom pretrained tokenizers) to your dependency budget; image-token geometry constants belong to OpenAI pricing rules, so gate them behind provider config if you support more vendors. Omit GET-request-based image dimension fetching in offline contexts — always pass `use_default_image_token_count=True` there.
