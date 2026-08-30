<!-- capsule-v2 -->
# ChatCompletions tool-output text coercion — how do tool results that are empty or non-text become valid ChatCompletions tool messages without silently losing data?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** The ChatCompletions API rejects empty/non-text tool messages — what is the exact degrade-vs-raise ladder for `function_call_output` items?

## Placeholder-or-raise ladder
**Path/Symbol:** `src/agents/models/chatcmpl_converter.py:` `Converter.items_to_messages` branch 5 (:820–855), constant `_OMITTED_TOOL_OUTPUT_PLACEHOLDER = "[tool output omitted]"` (:76), helpers `extract_all_content` (:430–531) / `extract_text_content` (:369–383).
**Signature:** branch inputs: `func_output["output"]` (str | iterable of content parts), flags `preserve_tool_output_all_content: bool`, `strict_feature_validation: bool`.
**Data Shape:** default path keeps only parts whose normalized type is `text`; a list result that ends up EMPTY (or was non-text-only) triggers the fallback; strict mode raises instead.

### Decisive source
```python
if preserve_tool_output_all_content:
    tool_result_content = cls.extract_all_content(output_content)
else:
    all_output_content = cls.extract_all_content(output_content)
    if isinstance(all_output_content, str):
        tool_result_content = all_output_content
    else:
        tool_result_content = [c for c in all_output_content if c.get("type") == "text"]
        if not tool_result_content:
            message = ("Chat Completions tool outputs cannot be empty or contain only "
                       "non-text content unless preserve_tool_output_all_content=True.")
            if strict_feature_validation:
                raise UserError(message)
            logger.warning("%s Replacing the tool output with a placeholder; enable strict "
                           "feature validation to raise an error instead.", message)
            tool_result_content = _OMITTED_TOOL_OUTPUT_PLACEHOLDER
msg: ChatCompletionToolMessageParam = {
    "role": "tool",
    "tool_call_id": func_output["call_id"],
    "content": tool_result_content,
}
```

**Flow:** string outputs pass through untouched → part lists normalize raw chat-completions aliases first (`text`→`input_text`, `image_url`→`input_image` via `_normalize_input_content_part_alias`, preserving `prompt_cache_breakpoint`) → mixed lists keep their text parts (no placeholder, no warning) → text-less/empty lists either raise (`strict_feature_validation=True`) or emit the `[tool output omitted]` placeholder with a logged warning → `preserve_tool_output_all_content=True` bypasses coercion entirely for providers that accept non-text tool results.
**Invariant:** every tool call in the replayed history still gets exactly one tool message with matching `tool_call_id`; degradation is observable (warning on the `openai.agents` logger) and never silent, and lossless mode remains available as an explicit opt-in rather than an implicit default.
**Probe:** `tests/models/test_openai_chatcompletions_converter.py::test_items_to_messages_with_empty_function_output_uses_placeholder_by_default` (:513 asserts content `== "[tool output omitted]"` + warning captured), `::test_items_to_messages_with_empty_function_output_raises_in_strict_mode` (:534), `::test_items_to_messages_with_mixed_function_output_keeps_text_by_default` (:546), `::test_items_to_messages_can_preserve_non_text_function_output` (:573).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "openai-agents-python", pattern: "_OMITTED_TOOL_OUTPUT_PLACEHOLDER", file_pattern: "*.py" });
await mcp.codebase_memory.check_index_coverage({ project: "openai-agents-python", paths: ["src/agents/models/chatcmpl_converter.py", "tests/models/test_openai_chatcompletions_converter.py"] });
```

## Verdict
Adopt the three-way ladder: keep-text-parts → warn+placeholder → strict UserError, plus the all-content opt-in flag. Adopt the invariant that a coerced message must still satisfy the wire contract (never send `[]`). Adapt the placeholder string and log channel to your SDK. Omit alias normalization for image/video/audio/file parts if your input layer already emits canonical shapes. Coverage: no_recorded_issue @ gen 2026-08-24T14:05:06Z.
