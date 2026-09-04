<!-- capsule-v2 -->
# Message-list cleaning — how do internal roles, images, and consecutive same-role turns become a provider-safe prompt?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What transformations does `get_clean_message_list` apply (role conversion, image encoding, same-role merging), and why must it deepcopy before mutating?

## Convert → encode → merge pipeline
**Path/Symbol:** `src/smolagents/models.py:get_clean_message_list` (:332-397), `tool_role_conversions` (:282-285), `MessageRole` (:111-120), image helpers `encode_image_base64`/`make_image_url` (`utils.py:430-437`).
**Signature:** `get_clean_message_list(message_list, role_conversions={}, convert_images_to_image_urls=False, flatten_messages_as_text=False) -> list[dict]`; accepts mixed `ChatMessage | dict` input.
**Data Shape:** Output dicts `{role, content}` where content is either the flattened text string or a list of typed parts (`text` / `image_url{url:data:image/png;base64,...}` / `image{image:<b64>}`).

### Decisive source
```python
message_list = deepcopy(message_list)  # Avoid modifying the original list  (:349)
...
if len(output_message_list) > 0 and message.role == output_message_list[-1]["role"]:
    if flatten_messages_as_text:
        output_message_list[-1]["content"] += "\n" + message.content[0]["text"]
    else:
        for el in message.content:
            if el["type"] == "text" and output_message_list[-1]["content"][-1]["type"] == "text":
                output_message_list[-1]["content"][-1]["text"] += "\n" + el["text"]   # merge adjacent texts
            else:
                output_message_list[-1]["content"].append(el)
```

**Flow:** Per message: validate role ∈ enum values; apply conversions (`TOOL_CALL→assistant`, `TOOL_RESPONSE→user`) so OpenAI-style APIs never see smolagents' synthetic roles; encode PIL parts to b64 inline or data-URL form; then merge with the previous message ONLY when roles match after conversion. Merging is content-type-aware: consecutive text parts concatenate with `\n`, but an image part starts a new part rather than corrupting text. The memory plane relies on this: ActionStep emits assistant-output + tool-call + observation as separate messages that collapse into provider-legal alternation.
**Invariant:** Deepcopy-first is load-bearing — the encoder POPS the raw `image` out of each part; without the copy, one generate() destroys the agent's memory images and every later step sends nothing. The role-conversion map is per-provider overridable (`custom_role_conversions`, e.g. Bedrock maps everything to user).
**Probe:** `tests/test_models.py::test_get_clean_message_list_basic/:_with_dicts/:_role_conversions/:_image_encoding/:_flatten_messages_as_text` (:686-797). Live: two same-role USER text ChatMessages in → one dict with `"a\nb"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "get_clean_message_list tool_role_conversions flatten_messages", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt convert→encode→merge with the deepcopy guard. Adapt the conversion table per provider's role vocabulary. Omit image handling only for text-only hosts, keeping the assert that forbids images under flattening.
