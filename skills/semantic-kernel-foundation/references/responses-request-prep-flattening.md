<!-- capsule-v2 -->
# Responses request-prep flattening — one pass from ChatHistory to Responses-API input items

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Which history items survive the Responses API request-prep pass, in what wire shape, and why do multiple images in one message not duplicate?

## ResponsesAgentThreadActions._prepare_chat_history_for_request
**Path/Symbol:** `python/semantic_kernel/agents/open_ai/responses_agent_thread_actions.py:ResponsesAgentThreadActions._prepare_chat_history_for_request` (lines 765–889).
**Signature:** `def _prepare_chat_history_for_request(cls, chat_history: "ChatHistory", store_enabled: bool) -> Any` (returns `list[dict | ...]` of raw response items + role/content dicts).
**Data Shape:** Output is a flat list mixing two shapes: bare dicts for function items (`{"type": "function_call", ...}` / `{"type": "function_call_output", ...}`) and `{"role": ..., "content": [{"type": "input_text"|"output_text"|"input_image"|"input_file", ...}]}` for message content. One output message per history message that has surviving items.

### Decisive source
```python
response_inputs: list[Any] = []
for message in chat_history.messages:
    allowed_items = [i for i in message.items
                     if not isinstance(i, (AnnotationContent, StreamingAnnotationContent))]
    if not allowed_items:
        continue
    original_role = message.role
    if original_role == AuthorRole.TOOL:
        original_role = AuthorRole.ASSISTANT
    contents: list[dict[str, Any]] = []
    for content in filtered_msg.items:
        match content:
            case TextContent() | StreamingTextContent():
                text_type = "input_text" if original_role == AuthorRole.USER else "output_text"
                contents.append({"type": text_type, "text": final_text})
            case ImageContent():
                image_url = content.data_uri or str(content.uri)  # neither set -> ValueError
                contents.append({"type": "input_image", "image_url": image_url})
            case FunctionCallContent():
                if not store_enabled:
                    response_inputs.append({"type": "function_call", "call_id": content.call_id,
                                            "name": content.name, "arguments": content.arguments})
            case FunctionResultContent():
                response_inputs.append({"type": "function_call_output", "output": str(content.result),
                                        "call_id": content.call_id})
            case BinaryContent() if content.can_read:
                contents.append({"type": "input_file", "filename": f"{uuid.uuid4()}{extension}",
                                 "file_data": f"data:{content.mime_type};base64,{content.data_string}"})
    if contents:
        response_inputs.append({"role": original_role, "content": contents})
```

**Flow:** Single pass over history. Annotation items are dropped; messages left empty by the
filter are skipped entirely. TOOL-role messages are rewritten to ASSISTANT (the Responses API has
no tool role for input). Text becomes `input_text` for USER messages, `output_text` otherwise —
the role decision uses the ORIGINAL role, evaluated before any rewrite matters. Images require
`data_uri` or `uri` (else `ValueError`). Function calls are re-sent ONLY when `store_enabled` is
false (the server already holds them otherwise); function results are always re-sent as
`function_call_output` with `str(result)`. Binary content becomes `input_file` with a uuid
filename and a mime-derived extension (pdf/txt/image/audio/other; image/audio misuse of
BinaryContent only warns). The message dict is appended only when `contents` is non-empty.
**Invariant:** Exactly one output message per surviving history message, items in original order
with no duplication — the flattening is one-pass and additive, never re-reading earlier messages.
This is what the "multiple images" test pins: 1 text + 4 images in one message produce exactly
one input message with exactly 5 content items in order. The pass-through philosophy is
deliberate: raw response items from previous rounds are forwarded untouched so reasoning and
function-call items survive intact.
**Probe:** `python/tests/unit/agents/openai_responses/test_openai_responses_thread_actions.py::test_prepare_chat_history_multiple_images_no_duplication` (line 513 — asserts len(result)==1, 1 input_text, 4 input_image in exact URL order, 5 total items).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "ResponsesAgentThreadActions _prepare_chat_history_for_request store_enabled function_call_output input_image", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the one-pass flattening with per-item wire-shape mapping, the TOOL→ASSISTANT role rewrite,
and the store_enabled gate on function-call re-sending. Adapt the content-type match to your
provider's input item taxonomy. Omit the BinaryContent filename heuristics if your host handles
file uploads out of band.
