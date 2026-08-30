<!-- capsule-v2 -->
# ToolReturnContent recursive rehydration — how do multimodal objects nested inside arbitrary tool-return dicts survive a JSON round-trip?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How can `BinaryContent`/`FileUrl` objects nested arbitrarily deep inside tool-return payloads reconstruct as typed objects after deserialization, without smart-union resolution flattening them into plain dicts?

## `_tool_return_content_discriminator` + recursive TypeAliasType + passthrough wrap validator/serializer
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/messages.py:_tool_return_content_discriminator` (:1165–1195), `ToolReturnContent` runtime definition (:1227–1249), `_validate_multimodal_or_passthrough` (:1198–1211), `_serialize_multimodal_or_passthrough` (:1214–1224), `_MULTIMODAL_KINDS`/`_MULTIMODAL_FIELDS` (:1156–1162), `tool_return_content_ta` (:1252).
**Signature:** `_tool_return_content_discriminator(value: Any) -> Literal['multimodal','mapping','sequence','any']`; `ToolReturnContent = TypeAliasType('ToolReturnContent', Annotated[multimodal|mapping|sequence|any tagged union, Discriminator(...)])`.
**Data Shape:** The multimodal branch gate requires a matching `kind` value (from the dumped union members) PLUS at least one type-specific field: `url`, `media_type`, or `file_id`. Both validate and serialize wrap handlers fall back to the raw value on failure/unmatched instance.

### Decisive source
```python
# messages.py:1180-1190 — kind alone is NOT enough
def _tool_return_content_discriminator(value):
    if isinstance(value, MULTI_MODAL_CONTENT_TYPES): return 'multimodal'
    if isinstance(value, Mapping):
        if ('kind' in value and isinstance(value['kind'], str)
                and value['kind'] in _MULTIMODAL_KINDS
                and any(field in value for field in _MULTIMODAL_FIELDS)):
            return 'multimodal'
        return 'mapping'

# messages.py:1208-1211 — heuristic failure degrades to passthrough, never raises
try:
    return handler(value)
except pydantic.ValidationError:
    return value
```

**Flow:** dict arrives → discriminator checks `kind ∈ multimodal kinds` AND presence of `url`/`media_type`/`file_id` → matched: validated as MultiModalContent (nested BinaryContent/FileUrl objects reconstructed); unmatched: stays a plain mapping. On serialization the mirror handler avoids routing non-multimodal passthrough dicts through the MultiModalContent serializer (which would emit spurious unexpected-value warnings). Because the alias is wired into the core `ToolReturnContent` type, every tool-return everywhere runs this discrimination via `ModelMessagesTypeAdapter`.

**Invariant:** Smart-union resolution would otherwise pick `Mapping[str, ToolReturnContent]` for a dumped multimodal dict (`{'kind': 'binary', ...}`) and skip the discriminated branch — leaving nested multimodal leaves as plain dicts forever. But kind-matching alone over-matches user dicts that merely reuse a `kind` string, so the second field requirement is load-bearing; and even then a shape-invalid lookalike must degrade to passthrough rather than raise (a hard ValidationError would break tools returning ordinary dicts). JSON-mode byte fidelity matters too: bytes serialize base64 via the shared config.

**Probe:** `tests/test_messages.py:1587` guards the type-specific-field gate; `tests/test_messages.py:1628` pins that without the explicit Discriminator smart-union picks Mapping/Any in python mode; `tests/test_messages.py:1635` exercises nested-dict reconstruction; `tests/test_messages.py:1668` documents the guard applies to every tool return through the core alias.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_tool_return_content_discriminator ToolReturnContent _validate_multimodal_or_passthrough tool_return_content_ta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-key discriminator gate (kind + type-specific field) with ValidationError→passthrough on both validate and serialize sides whenever you need typed-object rehydration inside untyped payloads. Adapt field sets to your own multimodal union members. Omit nothing — the fallbacks are the safety net that keeps ordinary user dicts working.
