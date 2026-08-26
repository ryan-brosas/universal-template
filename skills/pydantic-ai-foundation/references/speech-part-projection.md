<!-- capsule-v2 -->
# Speech-part projection — how does realtime audio history become text/audio any standard model can consume?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What do user/assistant `SpeechPart`s turn into on the way to a non-realtime model, and where must the barge-in interruption be made visible?

## `_convert_speech_parts`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/__init__.py:_convert_speech_parts` (:1929–1981); called first in `Model.prepare_messages` (:724). Speaker invariants enforced at construction: `ModelRequest.__post_init__` (:1865–1872, speaker must be 'user'), `ModelResponse.__post_init__` (:2604–2611, 'assistant').
**Signature:** `_convert_speech_parts(messages: list[ModelMessage], *, include_audio: bool) -> list[ModelMessage]`.
**Data Shape:** User side: retained audio (when `include_audio` and audio kept) → `UserPromptPart(content=[audio])`; else transcript → `UserPromptPart(content=transcript)`; neither → dropped. Assistant side: transcript (+ interruption marker lines) → `TextPart`. Messages left partless are dropped. Returns the ORIGINAL list when no SpeechPart exists anywhere — the identity check lets `_make_request` skip the redundant `_clean_message_history` pass.

### Decisive source
```python
# models/__init__.py:1957-1975 — the interruption marker is written on the way to
# the model and never persisted; history keeps it on SpeechPart.interrupted_at_ms
last_speech = max((i for i, p in enumerate(message.parts) if isinstance(p, SpeechPart)), default=None)
for index, part in enumerate(message.parts):
    if isinstance(part, SpeechPart):
        lines = [part.transcript] if part.transcript else []
        if part.interrupted_at_ms is not None:
            lines.append(f'[Interrupted after {part.interrupted_at_ms} ms]')
        elif message.state == 'interrupted' and index == last_speech:
            # The provider reported the interruption without an offset.
            lines.append('[Interrupted]')
        if lines:
            response_parts.append(TextPart(content='\n'.join(lines)))
```

**Flow:** realtime session stores SpeechParts with `interrupted_at_ms` offsets → standard model request → prepare_messages converts: user parts to prompts (audio or transcript), assistant parts to text → a barge-in cut mid-sentence gets an inline `[Interrupted ...]` marker so the model doesn't read the fragment as a complete utterance and repeat itself.

**Invariant:** The marker is EPHEMERAL — written here per-request, never persisted into stored history (the durable record of interruption lives on the part's `interrupted_at_ms` / message state). Without it, a truncated assistant turn looks finished and models echo-complete it. Assistant audio WITHOUT a transcript has nothing to send; same for user audio when retention was off.

**Probe:** `tests/test_streaming.py` realtime-interruption rendering pins both marker branches; `tests/test_messages.py` ModelRequest/ModelResponse `__post_init__` speaker-validation tests pin the construction-time invariant that makes the conversion unambiguous.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_convert_speech_parts interrupted_at_ms SpeechPart include_audio", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-side projection, the ephemeral interruption-marker rule, and the identity-return fast path. Adapt marker wording to your product voice. Omit the realtime session internals (duplex streaming, retention config) — they live above this seam.
