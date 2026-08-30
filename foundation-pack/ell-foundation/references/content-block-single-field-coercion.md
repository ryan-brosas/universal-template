<!-- capsule-v2 -->
# content block single-field coercion — how do heterogeneous inputs become validated single-payload blocks?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I accept "anything" as message content (str, image, tool call, parsed model, tool result) while guaranteeing each block carries exactly one payload?

## ContentBlock coerce + check_single_non_null
**Path/Symbol:** `src/ell/types/message.py:ContentBlock` (:125-151 `__init__` + `check_single_non_null`, :180-259 `coerce`, :74-117 `ImageContent.coerce`).
**Signature:** `ContentBlock.coerce(content: AnyContent) -> ContentBlock`; `ImageContent.coerce(value: Union[str, np.ndarray, PILImage.Image, ImageContent]) -> ImageContent`.
**Data Shape:** six mutually exclusive optional fields — `text | image | audio | tool_call | parsed | tool_result`; `AnyContent` union mirrors them plus raw numpy/PIL.

### Decisive source
```python
# message.py:146-151
@model_validator(mode='after')
def check_single_non_null(self):
    non_null_fields = [field for field, value in self.__dict__.items() if value is not None]
    if len(non_null_fields) > 1:
        raise ValueError(f"Only one field can be non-null. Found: {', '.join(non_null_fields)}")
    return self
```

```python
# message.py:94-103 — image string disambiguation
if isinstance(value, str):
    if value.startswith('http://') or value.startswith('https://'):
        return cls(url=value)
    try:
        img_data = base64.b64decode(value)
        img = PILImage.open(BytesIO(img_data))
        if img.mode not in ('L', 'RGB', 'RGBA'):
            return cls(image=img.convert('RGB'))
    except:
        raise ValueError("Invalid base64 string or URL for image")
```

**Flow:** constructor pre-processes `image=` kwargs through `ImageContent.coerce` (legacy `image_detail=` kwarg copied onto the coerced object), then pydantic validation runs; the after-validator enforces single-payload. Coercion ladder: ContentBlock→identity, str→text, ToolCall→tool_call, ToolResult→tool_result, image-like→image (numpy needs ndim==3 with 3/4 channels), BaseModel→parsed, else ValueError.
**Invariant:** exactly one payload per block is what makes downstream provider translation total (each translator can switch on `.type`); a porter allowing multi-payload blocks must rewrite every consumer. Non-RGB images are normalized to RGB at the boundary so serializers never see exotic modes.
**Probe:** `tests/test_message_type.py:test_content_block_single_non_null` (valid one-field cases + `pytest.raises(ValueError)` on two fields); `test_content_block_image_validation` (PIL ok, `"image.jpg"` path-string rejected); `test_content_block_coerce_content_block` (identity return).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "content block coerce", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.tests.test_message_type.test_content_block_coerce_content_block @ tests/test_message_type.py:58-61
```

## Verdict
Adopt single-payload validation with a discriminator property (`ContentBlock.type` returns the non-null field name) and the coercion ladder. Adapt the accepted image input set to your stack. Omit the legacy `image_detail` kwarg shim unless you need backward compatibility with an older wire format.
