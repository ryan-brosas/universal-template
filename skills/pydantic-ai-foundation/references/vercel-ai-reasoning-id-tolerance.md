<!-- capsule-v2 -->
# Client-side protocol ID fields — when a client sends an ID your model doesn't use, where does it go?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (vercel_ai adapter); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A stricter request schema rejects the AI SDK client's reasoning-part `id` and breaks every client that sends it — how do you accept a foreign ID without corrupting your internal identity mapping?

## vercel-ai-reasoning-id-tolerance
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py:` `ReasoningUIPart.id` field (:46); consumption in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/_adapter.py` (`ReasoningUIPart` → `ThinkingPart` at :396–406).
**Signature:** `id: str | None = Field(default=None, exclude_if=lambda value: value is None)`.
**Data Shape:** inbound UI part carries BOTH the AI SDK client id (top-level `.id`) AND the provider id nested in `providerMetadata.pydantic_ai.id`; only the nested one maps to `ThinkingPart.id`.

### Decisive source
```python
class ReasoningUIPart(BaseUIPart):
    type: Literal['reasoning'] = 'reasoning'

    id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    """UI part ID from the AI SDK client; not mapped to `ThinkingPart.id`."""
```
```python
# _adapter.py :396-406 — the nested providerMetadata id, NOT part.id, becomes ThinkingPart.id:
elif isinstance(part, ReasoningUIPart):
    provider_meta = load_provider_metadata(part.provider_metadata)
    builder.add(
        ThinkingPart(
            content=part.text,
            id=provider_meta.get('id'),
            signature=None if part.state == 'streaming' else provider_meta.get('signature'),
            ...
        )
    )
```

**Flow:** client sends reasoning part with optional top-level `id` → schema now ACCEPTS it (was: validation error #7706) → adapter ignores it for identity and keeps using the nested provider-metadata id → on outbound encode the field round-trips ONLY when set (`exclude_if` drops `None`, keeping serialized history byte-stable for cache prefixes).
**Invariant:** three rules:
1. Accept-and-quarantine foreign IDs: widen the wire schema with an optional field rather than rejecting unknown-but-meaningful client data; document its non-mapping explicitly in the docstring.
2. Two-ID discipline: client-side display ids and provider-side content ids are DIFFERENT namespaces — never let one overwrite the other during load_messages.
3. `exclude_if`-style conditional serialization keeps absent fields absent on re-encode; without it, every echoed history gains `"id": null` noise that breaks byte-compare caches.
**Probe:** `tests/test_vercel_ai.py::test_build_run_input_reasoning_part_id_mapping` (:159–211, three-case parametrize: absent → `(None, None)`; ui-only → `('ui-r1', None)`; ui+providerMetadata → `('ui-r1', 'provider-r1')`) + `test_reasoning_part_id_serialization` (:214–215, `'id' not in …model_dump()`) — both EXECUTED GREEN in repo `.venv` this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "ReasoningUIPart id run input thinking mapping vercel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt accept-and-quarantine for client-originated ID fields with conditional serialization; adapt field names to your wire protocol; omit nothing — this is a small but exactly-shaped seam for any host embedding a third-party chat protocol.
