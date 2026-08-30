<!-- capsule-v2 -->
# Reasoning-details codec — OpenRouter reasoning_details ↔ ThinkingPart round-trip

## Source / Question
`pydantic_ai_slim/pydantic_ai/models/_reasoning_details.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** The `reasoning_details` wire format (OpenRouter-originated; adopted by Snowflake Cortex et al.) carries provider-specific reasoning blobs with a `type` AND a `format` field — how do you map them losslessly to a unified ThinkingPart and back so replayed requests keep vendor opaqueness? A porter will flatten the details into text and destroy the encrypted/signature payloads.

## Path / Symbol
`models/_reasoning_details.py` — whole file: `BaseReasoningDetail` + `ReasoningSummary`/`ReasoningEncrypted`/`ReasoningText` frozen models (:17–46), `from_reasoning_detail()` (:58–83), `into_reasoning_detail()` (:85–117).

## Signature
```python
def from_reasoning_detail(reasoning: ReasoningDetail, provider_name: str) -> ThinkingPart
def into_reasoning_detail(thinking_part: ThinkingPart) -> ReasoningDetail | None  # None when no provider_details
```

## Data Shape
Each detail: `{type: 'reasoning.text'|'reasoning.summary'|'reasoning.encrypted', format: 'anthropic-claude-v1'|'openai-responses-v1'|..., id, index}`. Mapping into ThinkingPart fields: text → content+signature; summary → content; encrypted → content='' + signature=data. `provider_name` + the dumped `{format,index,type}` ride along as `provider_details` — the opaque round-trip payload.

### Decisive source — the encrypted leg (:74–83, :108–114)
```python
elif isinstance(reasoning, ReasoningEncrypted):
    return ThinkingPart(id=reasoning.id, content='', signature=reasoning.data,
                        provider_name=provider_name, provider_details=provider_details)
...
elif data.type == 'reasoning.encrypted':
    assert thinking_part.signature is not None
    return ReasoningEncrypted(type=data.type, id=thinking_part.id, format=data.format,
                              index=data.index, data=thinking_part.signature)
```

**Flow:** inbound wire detail → validate as the discriminated union → project onto ThinkingPart keeping the ORIGINAL detail dict (minus payload) in provider_details → history persists it → outbound: `into_reasoning_detail` re-validates the stored dict, dispatches on its `type`, and re-fills payload fields from content/signature. Unknown type hits `assert_never`. `None` provider_details ⇒ None return (part carries no reasoning_details leg).

**Invariant:** Encrypted reasoning must survive a full history round-trip byte-opaque: signature field IS the encrypted blob on both legs; type/format/id/index never mutate; the codec is the ONLY place that interprets these dicts — everything downstream treats provider_details as opaque.

**Probe:** `tests/models/test_openrouter.py` :281–333 — asserts `reasoning_details` presence/shape incl. summary+encrypted pair ordering and exact echo on replay. Coverage caveat: codec unit tests live inside the openrouter model suite, not a dedicated file.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'from_reasoning_detail into_reasoning_detail ReasoningEncrypted'
```

## Verdict
**Adopt** the codec pattern (opaque provider_details + typed discriminator) for any multi-provider reasoning passthrough. **Adopt** encrypted-as-signature identity. **Adapt** the detail vocabulary as upstream formats grow. **Omit** nothing.
