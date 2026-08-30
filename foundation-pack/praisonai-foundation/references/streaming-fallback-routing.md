<!-- capsule-v2 -->
# Streaming fallback routing — which exceptions may trigger the non-streaming fallback, and which must never?

**Source:** praisonai MIT `main@d82364ec23a83fd9a6e2e849a5285442b4734ca3`; Codebase Memory `praisonai`. **Question:** When `stream=None` auto-detect tries streaming first, exactly which exceptions from that attempt are safe to downgrade to a non-streaming retry — and which ones must be re-raised because a second attempt would double-execute side effects or double-retry?

## ChatMixin._chat_completion streaming auto-detect ladder
**Path/Symbol:** `src/praisonai-agents/praisonaiagents/agent/chat_mixin.py:ChatMixin._chat_completion` (lines 1844–1880; async parity twin at line 2372).
**Signature:** inside `_chat_completion(self, messages, temperature=None, tools=None, stream=None, ...)`; when `stream is None` the first attempt calls `_chat_completion_with_retry(..., stream=True, stream_callback=self.stream_emitter.emit if available, emit_events=True)`; on downgrade it sets `stream = False` and the main dispatch below reuses the same helper with the final value.

### Decisive source
```python
if stream is None:
    # Auto-detect: prefer streaming for better UX, fallback if adapter doesn't support it
    try:
        stream_callback = self.stream_emitter.emit if hasattr(self, 'stream_emitter') else None
        streaming_response = self._chat_completion_with_retry(
            messages=messages, ..., stream=True,  # Try streaming first
            stream_callback=stream_callback, emit_events=True
        )
    except ValueError as e:
        if "Streaming is not supported" in str(e):
            # Fallback: retry with non-streaming for sync adapters
            logging.debug(f"{self.name}: Streaming not supported by adapter, falling back to non-streaming")
            stream = False  # Set for the main execution below
        else:
            raise  # Re-raise if it's a different ValueError
    except ToolExecutionError:
        # A tool failed during the streaming attempt. Re-raise so it is
        # not relabelled as an LLM error and so the tool is not executed
        # a second time by the non-streaming fallback below.
        raise
    except Exception as e:
        from ..errors import LLMError
        # Don't retry if it's an LLMError that has exhausted retries
        if isinstance(e, LLMError):
            raise  # Re-raise LLMErrors immediately to avoid double retry
        # For any other exception, fall back to non-streaming
        logging.debug(f"{self.name}: Streaming attempt failed, falling back to non-streaming")
        stream = False  # Set for the main execution below
```

**Flow:** `stream=None` → try streaming first (better UX) → classify the failure: (1) `ValueError` whose message contains the exact marker "Streaming is not supported" → the only downgrade path, set `stream=False` for the main dispatch; (2) any other `ValueError` → re-raise; (3) `ToolExecutionError` → re-raise unconditionally (a tool already executed during the streaming attempt must not run a second time); (4) `LLMError` → re-raise immediately (its internal retry budget is exhausted; a non-streaming attempt would double-retry); (5) any other exception → downgrade to non-streaming. A successful streaming response short-circuits the main dispatch (`final_response = streaming_response`).
**Invariant:** the downgrade decision is allow-listed by exception *type AND message* — only the exact "Streaming is not supported" `ValueError` may trigger it; anything that can have side effects (`ToolExecutionError`) or has already consumed its retry budget (`LLMError`) must propagate unchanged; an explicit `stream=True/False` from the caller never triggers auto-detect.
**Probe:** no dedicated direct test of this ladder exists in tests/ at the pin → deterministic-read caveat. Nearest pin: `tests/unit/agents/test_multiagent_streaming_fix.py:43` matches the adapter's exact message string `"Streaming is not supported in sync OpenAIAdapter"` — the substring contract the ladder keys on.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "praisonai", query: "streaming not supported fallback non-streaming ToolExecutionError", name_pattern: "^_chat_completion_with_retry$", limit: 10 });
```

## Verdict
Adopt the allow-listed-downgrade pattern: try the better-UX mode first, but gate the fallback on an exact type+message match, and give *side-effect-bearing* and *budget-consumed* error classes their own re-raise branches BEFORE the generic catch — ordering matters, the `ToolExecutionError` branch exists precisely so the generic `except Exception` cannot swallow it into a double tool execution. Adapt the marker string to your adapter layer's capability error (define one dedicated exception instead of message matching if you own both sides). Omit praisonai's `stream_emitter` event plumbing. Coverage: no recorded index issue on chat_mixin.py; the ladder itself is untested directly — verify by trace before porting.
