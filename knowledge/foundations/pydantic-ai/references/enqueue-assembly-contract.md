<!-- capsule-v2 -->
# Enqueue assembly — variadic items coalesce into messages that must end in a ModelRequest

## Source / Question
`pydantic_ai_slim/pydantic_ai/_enqueue.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a tool mid-run calls `enqueue('caption', image, SystemPromptPart(...), some_model_response)`, how do heterogeneous items become well-formed history without letting an assembled sequence end in something the agent can't respond to? A porter will append each item as its own message and ship interleaved turns that break wire merging.

## Path / Symbol
`_enqueue.py` — `_build_enqueue_messages` (:69–118), `PendingMessage.from_content` (:147–166), `PendingMessage` dataclass (:121–166), `EnqueueContent` alias (:45), `PendingMessagePriority` (:33–42).

## Signature
```python
def _build_enqueue_messages(items: Sequence[EnqueueContent]) -> list[ModelMessage]: ...
@classmethod
def from_content(cls, *content: EnqueueContent,
                 priority: PendingMessagePriority = 'asap') -> PendingMessage | None: ...
```

## Data Shape
`EnqueueContent = UserContent | ModelRequestPart | ModelMessage`. Three item classes drive three accumulation buckets: user content (`str`/multimodal) gathers into `content`; part-style items (`SystemPromptPart`, `UserPromptPart`, `ToolReturnPart`, `RetryPromptPart`, `ToolSearchReturnPart`, `ToolAvailabilityDeltaPart`, `SpeechPart`) gather into `parts`; complete `ModelRequest`/`ModelResponse` flush everything and emit themselves. `flush_content` collapses a lone string to bare `str` content (matching `Agent.run('...')`), anything else becomes a content list.

### Decisive source — ordered single-pass assembly with two flushes (:97–118)
```python
for item in items:
    if isinstance(item, (ModelRequest, ModelResponse)):
        flush_request()
        messages.append(item)
    elif isinstance(item, (SystemPromptPart, UserPromptPart, ...)):
        flush_content()
        parts.append(item)
    else:
        content.append(item)
flush_request()
```
`from_content` returns `None` for an empty call (enqueue-nothing is a no-op, not an error) and raises `UserError` when `messages[-1]` is not a `ModelRequest` — e.g. a lone `ModelResponse` — because "the agent needs a request to respond to."

**Flow:** iterate once → complete message flushes pending parts+content first (so `ModelResponse` followed by strings yields response then request, enabling one call to inject a synthetic exchange) → part item closes any open content run and joins the current parts bucket → trailing `flush_request()` closes the final request → terminal-kind check.

**Invariant:** Order is preserved and adjacent same-class items coalesce; the assembled list MUST end in a `ModelRequest` or construction fails loud. A `PendingMessage` with an empty-parts `ModelRequest` is legal (drain stamps and forwards it; downstream wire-merging absorbs zero-part messages).

**Probe:** `tests/test_capabilities.py::test_single_enqueue_with_multiple_messages_emits_one_event` (:17609 region) pins response-then-request injection delivering exactly two messages under one `enqueue_id`; `test_pending_message_positional_construction_keeps_priority_second` (:16911) pins field order (`enqueue_id`'s generated default must stay AFTER `priority` so positional callers don't silently assign priority into the id); `test_enqueue_lone_response_raises_user_error` (:17940 region) pins the must-end-in-request error through a real run; `test_pending_message_allows_empty_request` (:17621).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query '_build_enqueue_messages PendingMessage from_content flush'
```

## Verdict
**Adopt** the three-bucket ordered assembler, the lone-string collapse, the empty-call→None contract, and the terminal-request validation verbatim for any tool-facing message queue. **Adapt** the part-type enumeration to your host's message vocabulary; keep the field order discipline (generated-default id last) if you keep dataclass positionality. **Omit** the drain side (priority delivery is `pending-message-drain-redirect.md`'s seam).
