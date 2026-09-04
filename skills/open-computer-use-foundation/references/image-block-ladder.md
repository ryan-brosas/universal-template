<!-- capsule-v2 -->
# Image block encoding ladder — how do raw screenshot bytes become provider-correct image content blocks?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** How does one message shape (list mixing str + bytes) get transformed into OpenAI data-URLs vs Anthropic base64 sources?

## transform_message → wrap_block → create_image_block per provider family
**Path/Symbol:** `os_computer_use/llm_provider.py:71-85` (`wrap_block`, `transform_message`), `:122-136` (`OpenAIBaseProvider.create_image_block`), `:191-199` (`AnthropicBaseProvider.create_image_block`).
**Signature:** `transform_message(message) -> message` (content list → wrapped list; non-list passes through untouched); `create_image_block(image_data: bytes) -> dict`.
**Data Shape:** Canonical agent message = `{"role": str, "content": [str|bytes, …]}` from the `Message()` factory (`:11-12`). Bytes mean "image"; strings pass through as `Text`. Anthropic's variant accepts a base64 STRING, not bytes.

### Decisive source
```python
def wrap_block(self, block):
    if isinstance(block, bytes):
        # Pass raw bytes so that imghdr can detect the image type properly.
        return self.create_image_block(block)
    else:
        return Text(block)
```
```python
# OpenAI: sniff format via Pillow, default png on failure
image_type = "png"  # Default to PNG if detection fails
try:
    with Image.open(io.BytesIO(image_data)) as img:
        image_type = img.format.lower()
except Exception as e:
    print(f"Error detecting image type: {e}")
encoded = base64.b64encode(image_data).decode("utf-8")
return {"type": "image_url",
        "image_url": {"url": f"data:image/{image_type};base64,{encoded}"}}
```
```python
# Anthropic: hardcoded png media type
return {"type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": base64_image}}
```

**Flow:** every outgoing message passes through `transform_message` in `completion()` → per-element dispatch on `isinstance(bytes)` → provider-specific block construction → kwargs filtered (`None` tools omitted) before `client.create`.
**Invariant:** The bytes-in-content convention is the portability boundary — providers never see raw bytes because EVERY call re-wraps; OpenAI sniffs the real format and falls back to png WITHOUT failing the call, while Anthropic hardcodes `image/png` (a JPEG would be mislabeled — fine for E2B screenshots, wrong for arbitrary images). Detection failure is warn-and-continue, never raise.
**Probe:** `cd $REFERENCE_ROOT/external/open-computer-use && grep -n 'data:image' os_computer_use/llm_provider.py && grep -n 'media_type' os_computer_use/llm_provider.py` (pins f-string data-URL at :135 and hardcoded png at :196); direct test: `tests/llm_provider.py:27-35` builds exactly this mixed `[str, bytes]` content for five providers.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "wrap_block transform_message create_image_block base64", limit: 8, fields: ["signature", "name", "file"] });
// expect wrap_block / transform_message / both create_image_block overrides
```

## Verdict
Adopt the mixed-list content convention + per-provider block factory for any multi-provider vision agent; adapt media-type handling if you support non-PNG screenshots on Anthropic (add sniffing there); omit the silent png fallback only if your pipeline guarantees format upstream.
