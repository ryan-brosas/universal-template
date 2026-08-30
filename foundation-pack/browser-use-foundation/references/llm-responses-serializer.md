<!-- capsule-v2 -->
# Responses-API message serialization — how do you flatten a chat history into OpenAI Responses `input` items?

**Source:** browser-use MIT `main@85ddbfedf609166b2d2c76c3d80506649fee82a9`; Codebase Memory `mnt-hdd-utopia-inspo-agents-browser-use`. **Question:** what happens to images, refusals, and assistant tool calls when messages cross into the Responses API's easy-input shape?

## Role-differentiated content flattening
**Path/Symbol:** `browser_use/llm/openai/responses_serializer.py:23-143` (`ResponsesAPIMessageSerializer.serialize` :100, content serializers :27-85).
**Signature:** `serialize(message: BaseMessage) -> EasyInputMessageParam`; `serialize_messages(messages: list[BaseMessage]) -> list[EasyInputMessageParam]`.
**Data Shape:** in: internal message union (content = str | typed parts | None); out: `{role, content}` where content is a plain string OR a part list of `input_text`/`input_image`.

### Decisive source
```python
# Assistant content is text-only on this wire; refusals become visible text:
elif part.type == 'refusal':
    serialized_parts.append(ResponseInputTextParam(text=f'[Refusal: {part.refusal}]', type='input_text'))
# Assistant with NO content but tool calls → tool calls rendered as context text:
if content is None:
    if message.tool_calls:
        tool_call_text = '\n'.join(
            f'[Tool call: {tc.function.name}({tc.function.arguments})]' for tc in message.tool_calls)
        content = tool_call_text
    else:
        content = ''
```

**Flow:** dispatch by message class → user content passes text + image parts through (`image_url` → `input_image` keeping `detail`) → system content drops non-text parts silently → assistant content converts refusal parts to `[Refusal: …]` text and synthesizes placeholder text from tool calls when content is None (empty string when there are neither). Unknown message types raise `ValueError`.
**Invariant:** the Responses input format has no native slots for refusal or historical tool calls — dropping them would erase the model's own reasoning trail from context, so both degrade to VISIBLE TEXT placeholders instead of disappearing. System stays role `'system'` via EasyInputMessageParam (the `'developer'` role note in-source is context-specific); user images keep their detail hint.
**Probe:** `tests/ci/models/test_azure_responses_api.py::TestResponsesAPIMessageSerializer::test_serialize_assistant_message_none_content_with_tool_calls` (:97) and `…_no_tool_calls` (:114); 9 tests in the class cover the full matrix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-browser-use", query: "ResponsesAPIMessageSerializer EasyInputMessageParam serialize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the degrade-to-placeholder rule for wire formats that cannot represent a content kind. Adapt placeholder wording to your host. Omit the openai-types dependency if your target uses a different SDK — the contract (never silently drop content kinds) is the portable part.
