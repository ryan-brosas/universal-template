<!-- capsule-v2 -->
# ACP prompt content blocks — how do editor-supplied multimodal prompt blocks become model user-content without downgrading inline data?

**Source:** pydantic-ai-harness (MIT) `main@76db3dec`; Codebase Memory `pydantic-ai-harness`. **Question:** How should a protocol adapter translate foreign multimodal content blocks into a framework's user-content types when the wire format allows both inline bytes and URL references?

## Inline-first block translation
**Path/Symbol:** `pydantic_ai_harness/experimental/acp/_content.py:prompt_blocks_to_user_content` (:25–60), `_DEFAULT_BINARY_MEDIA_TYPE` (:22).
**Signature:** `prompt_blocks_to_user_content(blocks: Sequence[PromptContentBlock]) -> list[UserContent]`.
**Data Shape:** In: the five ACP block variants (`Text | Image | Audio | Resource | EmbeddedResource ContentBlock`). Out: an ordered list of plain strings, `BinaryContent(data=..., media_type=...)`, or `ImageUrl(url=...)`.

### Decisive source
```python
elif isinstance(block, schema.ImageContentBlock):
    # ACP requires inline `data`; `uri` is only an optional reference to the image's source.
    # Prefer the bytes the client actually sent, falling back to the URL only when no inline
    # data is present (a client sending both must not have its image silently replaced by a
    # link the model may be unable to fetch).
    if not block.data and block.uri is not None:
        content.append(ImageUrl(url=block.uri))
    else:
        content.append(BinaryContent(data=base64.b64decode(block.data), media_type=block.mime_type))
...
    media_type = resource.mime_type or _DEFAULT_BINARY_MEDIA_TYPE  # 'application/octet-stream'
```

**Flow:** text block → plain string; embedded **text** resource → its text string; embedded **blob** resource → base64-decoded `BinaryContent`, media type defaulting to `application/octet-stream` (an empty media type would raise later when formatted for a model request); resource **link** → labeled URI text `'My File (file:///a.txt)'` using `title or name`, bare URI if unlabeled; mixed blocks preserve list order.
**Invariant:** Inline data wins over a URI reference — a block carrying both keeps its bytes. An undeclared binary media type never reaches the model as an empty string. The function is total over the block union: the final `else` is safe because the link variant is the only one left.
**Probe:** `tests/experimental/acp/test_content.py` (whole file): `test_image_with_both_data_and_uri_prefers_inline_data`, `test_embedded_blob_resource_without_mime_type_uses_octet_stream`, `test_resource_link_prefers_title_over_name`, `test_mixed_blocks_preserve_order`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "prompt blocks to user content image data uri", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt inline-data-over-URI preference, the octet-stream fallback for undeclared blobs, and labeled-URI degradation for link-only references. Adapt the target content classes (`BinaryContent`/`ImageUrl`) to your framework's equivalents. Omit the acp-schema block union itself.
