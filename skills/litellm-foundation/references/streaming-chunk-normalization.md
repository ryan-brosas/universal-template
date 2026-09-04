<!-- capsule-v2 -->
# streaming-chunk-normalization — How do heterogeneous provider stream chunks become uniform OpenAI-shaped chunks, and when must a chunk be suppressed vs emitted?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** What is the dispatch → normalize → gate pipeline of `CustomStreamWrapper`, including the finish-reason deferral rule a porter will get wrong?

## Connected graph-selected seam
**Path/Symbol:** `litellm/litellm_core_utils/streaming_handler.py:CustomStreamWrapper._dispatch_provider_chunk` (:1176-1503), `chunk_creator` (:1504-1627), `return_processed_chunk_logic` (:1018-1138).
**Signature:** `chunk_creator(self, chunk: Any)` — returns `ModelResponseStream | None` (None = suppress this chunk).
**Data Shape:** Per-instance state machine: `received_finish_reason`, `sent_first_chunk`, `sent_last_chunk`, `holding_chunk`, `chunks` (usage-only accumulator), `intermittent_finish_reason`. Sentinel classes `_ProviderChunkParsed` / `_ProviderChunkEarlyReturn` let the dispatcher short-circuit.

### Decisive source
```python
            if chunk.choices and chunk.choices[0].finish_reason:
                self.received_finish_reason = chunk.choices[0].finish_reason
                if not _has_content:
                    return _ProviderChunkEarlyReturn(None)
                # Strip finish_reason from the content chunk so it appears
                # only on the trailing empty-delta chunk (OpenAI spec).
                # finish_reason_handler() will emit the proper terminal chunk.
                chunk.choices[0].finish_reason = None
            return _ProviderChunkEarlyReturn(chunk)
```

**Flow:** `_dispatch_provider_chunk` routes by provider family: custom-provider ModelResponseStream passthrough (with StopIteration once finished and no content) → generic-dict GChunk lane (anthropic-style `text/tool_use/usage/provider_specific_fields`) → per-vendor handlers (`handle_replicate_chunk`, `handle_predibase_chunk`, fake-streaming `handle_baseten/ai21/maritalk/nlp_cloud/aleph_alpha` which buffer whole responses then synthesize deltas, azure/openai text-completion lanes…). `chunk_creator` then: fixes mistral quirks (`role: None` → "assistant", `tool.type: None` → "function", None arguments → "") → tool-call promotion (`functions` param converts first tool_call to legacy function_call; sets `self.tool_call`) → usage attachment. Finally `return_processed_chunk_logic` gates emission: non-empty content → special-token filter (`check_special_tokens` may HOLD the chunk in `self.holding_chunk` to catch eos/bos strings) → role stripped from deltas after first chunk; post-finish → flush holding chunk into the terminal empty-delta chunk with mapped `finish_reason` and set `sent_last_chunk`; OpenRouter-style post-finish usage chunks still emit; everything else returns None (suppressed).

**Cross-cutting invariants a porter must keep:** (a) finish_reason appears ONLY on the trailing empty-delta chunk — content chunks carry it stripped; (b) "cannot set content of an OpenAI Object to be an empty string" — empty completions are suppressed, not emitted; (c) thinking blocks are optionally re-merged into one `<think>...</think>` chunk for UI consumers (`_optional_combine_thinking_block_in_choices`); (d) `preserve_upstream_non_openai_attributes` copies unknown attrs so provider-specific fields survive normalization on BOTH content and final chunks; (e) errors inside chunk_creator are re-mapped through `exception_type` so mid-stream failures surface as typed litellm exceptions (:1620-1627); (f) global wall-clock cap `LITELLM_MAX_STREAMING_DURATION_SECONDS` (None = unlimited) checked via `_check_max_streaming_duration`.
**Invariant:** Suppression (None return) is how the wrapper hides vendor noise; the ONLY post-finish emissions allowed are holding-chunk flushes and usage-bearing chunks.
**Probe:** `tests/test_litellm/litellm_core_utils/test_streaming_handler.py:test_chunk_creator_strips_finish_reason_from_content_chunk` (:3234-3264) pins the deferral invariant directly; siblings cover synthesized-finish-chunk cleanup (:4129-4213). Deterministic check: `grep -c "def test" tests/test_litellm/litellm_core_utils/test_streaming_handler.py` ≥ 20 at f005afa1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "CustomStreamWrapper chunk_creator finish_reason", limit: 10 });
```

## Verdict
Adopt the dispatch→normalize→gate shape plus the finish-reason deferral rule for any SSE normalizer. Adapt the per-vendor handler set to your providers; the fake-streaming handlers are copy-paste templates. Omit MCP-tool-chunk enrichment and thinking-block merging if you don't serve those features. Coverage caveat: none at this pin.
