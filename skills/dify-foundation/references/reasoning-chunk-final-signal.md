<!-- capsule-v2 -->
# reasoning-chunk-final-signal — How does "thinking finished" survive an empty final chunk?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What is the drop rule for reasoning (chain-of-thought) stream events?

## Empty reasoning drops EXCEPT when it carries the is_final terminator
**Path/Symbol:** `api/core/app/apps/workflow/generate_task_pipeline.py:_handle_reasoning_chunk_event` (:576-590).
**Signature:** `_handle_reasoning_chunk_event(event: QueueReasoningChunkEvent, **kwargs) -> Generator[StreamResponse]`.
**Data Shape:** Event fields `reasoning: str`, `from_node_id`, `is_final: bool`; yields `ReasoningChunkStreamResponse` with the same three fields plus task_id.

### Decisive source
```python
def _handle_reasoning_chunk_event(self, event, **kwargs):
    """Handle reasoning chunk events."""
    # is_final with empty reasoning is still forwarded as the "thinking finished" signal
    if not event.reasoning and not event.is_final:
        return
    yield ReasoningChunkStreamResponse(
        task_id=self._application_generate_entity.task_id,
        data=ReasoningChunkStreamResponse.Data(
            reasoning=event.reasoning,
            node_id=event.from_node_id,
            is_final=event.is_final,
        ),
    )
```

**Flow:** engine emits reasoning chunks as a model thinks → empty-text non-final chunks are dropped (pure noise suppression) → the terminating empty chunk (`is_final=True`) passes THROUGH so clients can close their "thinking" UI state even though no text rides it.
**Invariant:** The drop predicate is `not reasoning AND not is_final` — testing only emptiness would swallow the terminator and hang every client spinner; `is_final` semantics belong to the wire contract, not to payload presence.
**Probe:** `grep -c 'not event.reasoning and not event.is_final' core/app/apps/workflow/generate_task_pipeline.py` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_handle_reasoning_chunk_event is_final empty reasoning", limit: 10 });
```

## Verdict
Adopt the two-condition drop rule verbatim. Adapt response envelope. Omit nothing — one line, but getting it wrong hangs UIs.
