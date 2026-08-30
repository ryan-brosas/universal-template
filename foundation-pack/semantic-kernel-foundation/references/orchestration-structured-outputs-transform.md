<!-- capsule-v2 -->
# Orchestration structured-outputs transform — typed final output on a fresh kernel without mutating caller settings

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does an orchestration turn a free-form final message into a typed pydantic model without mutating the caller's settings object?

## structured_outputs_transform
**Path/Symbol:** `python/semantic_kernel/agents/orchestration/tools.py:structured_outputs_transform` (whole file, 67 ln; setup 25–51, closure 53–67).
**Signature:** `def structured_outputs_transform(target_structure: type[BaseModel], service: ChatCompletionClientBase, prompt_execution_settings: PromptExecutionSettings | None = None) -> Callable[[DefaultTypeAlias], Awaitable[BaseModel]]`.
**Data Shape:** Input `DefaultTypeAlias = ChatMessageContent | list[ChatMessageContent]`; output `target_structure.model_validate_json(response.content)`. A FRESH private `Kernel()` is built per transform; the service's typed settings are pulled from it via `get_prompt_execution_settings_from_service_id`.

### Decisive source
```python
kernel = Kernel()
kernel.add_service(service)

settings = kernel.get_prompt_execution_settings_from_service_id(service.service_id)
if prompt_execution_settings:
    settings.update_from_prompt_execution_settings(prompt_execution_settings)
if not hasattr(settings, "response_format"):
    raise ValueError("The service must support structured output.")
settings.response_format = target_structure

chat_history = ChatHistory(
    system_message=(
        "Try your best to summarize the conversation into structured format:\n"
        f"{target_structure.model_json_schema()}."
    ),
)

async def output_transform(output: DefaultTypeAlias) -> BaseModel:
    if isinstance(output, ChatMessageContent):
        chat_history.add_message(output)
    elif isinstance(output, list) and all(isinstance(item, ChatMessageContent) for item in output):
        for item in output:
            chat_history.add_message(item)
    else:
        raise ValueError(f"Output must be {DefaultTypeAlias}.")
    response = await service.get_chat_message_content(chat_history, settings)
    assert response is not None
    return target_structure.model_validate_json(response.content)
```

**Flow:** Setup (once per transform): fresh private Kernel → register the service → pull the service's OWN typed settings class → merge the caller's optional settings via `update_from_prompt_execution_settings` (the caller's object is never mutated — pinned by test) → gate on `hasattr(settings, "response_format")` (ValueError otherwise, so non-structured-output services fail at transform CONSTRUCTION, not mid-run) → bake the JSON schema into a system message and freeze the ChatHistory. Per call: accept a single ChatMessageContent or a list of them (anything else → ValueError), append to the accumulated history, one chat completion with the structured settings, `model_validate_json` the text.
**Invariant:** The caller's `prompt_execution_settings` object is never mutated (extension_data preserved verbatim — pinned by test); the transform is stateful ONLY in its private chat history, so one transform instance accumulates the whole conversation it summarizes. Unsupported services fail fast at construction.
**Probe:** `python/tests/unit/agents/orchestration/test_orchestration_tools.py::test_structured_outputs_transform_original_settings_not_changed` (line 60 — `not hasattr(prompt_execution_settings, "response_format")` and extension_data intact), `test_structured_outputs_transform_unsupported_service` (78 — ValueError for a settings class without response_format), `test_structured_outputs_transform_invoke` (95 — single message → 2 history messages), `test_structured_outputs_transform_invoke_with_messages` (126 — list → 3), `test_structured_outputs_transform_invoke_unsupported_type` (160 — ValueError).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "structured_outputs_transform output_transform response_format model_validate_json update_from_prompt_execution_settings", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the fresh-kernel + settings-clone + construction-time capability gate + schema-in-system-message pattern for any "summarize into a typed model" output hook. Adapt the settings-merge call to your host's settings-conversion seam. Omit the list-accepting arm if your orchestration always produces a single final message.
