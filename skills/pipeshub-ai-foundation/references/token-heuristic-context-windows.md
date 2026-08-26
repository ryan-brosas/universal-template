<!-- capsule-v2 -->
# Pre-call token heuristic + window pair — what do shaping decisions run on before the provider reports real usage, and which window pairs with external summarization?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How are tokens estimated for every-turn shaping decisions without a tokenizer — and why do two ContextWindow implementations exist when compaction middleware already exists?

## 4-chars-per-token estimate that must NEVER feed the budget ledger
**Path/Symbol:** `backend/python/app/agent_loop_lib/core/tokens.py:_CHARS_PER_TOKEN/_MESSAGE_OVERHEAD_TOKENS/extract_text/count_message_tokens` (:23 / :26 / :29 / :56) + `context/window.py:SlidingWindowContext._evict` (:19) + `context/manager.py:ContextManager`.
**Signature:** `count_message_tokens(message: Message) -> int`; `SlidingWindowContext(max_tokens=100_000)`; `ContextManager(max_tokens=100_000)`.
**Data Shape:** In: message list. Out: int estimates = `_MESSAGE_OVERHEAD_TOKENS + total_chars // _CHARS_PER_TOKEN`, where tool-call name+stringified args add chars. The docstring draws the boundary explicitly: this is deliberately NOT a real tokenizer; it runs every turn for every shaper BEFORE the provider's `TokenUsage` arrives.

### Decisive source
```python
# Every message costs a few tokens of protocol overhead (role marker,
# separators) regardless of content, on top of raw character count.
_CHARS_PER_TOKEN = 4
_MESSAGE_OVERHEAD_TOKENS = 4
...
while await self.token_count() > self._max_tokens:   # SlidingWindowContext
    # Find the index of the first non-SYSTEM message
    evicted = False
    for i, msg in enumerate(self._messages):
        if msg.role != MessageRole.SYSTEM:
            self._messages.pop(i); evicted = True; break
    if not evicted:
        break   # Only system messages remain — cannot evict further
```

**Flow:** Shapers/middlewares call `count_tokens(messages)` pre-call → truncate/evict/compact decisions ride the ESTIMATE → provider truth lands in `modules/providers/budget/tracker.py` (REAL usage for cost/limit enforcement). Two windows: `SlidingWindowContext` drops oldest NON-SYSTEM messages on overflow and keeps system messages on `clear()`; `ContextManager` NEVER evicts ("for use when external summarization handles trimming") — production agents (`factory.py:985`, `single_shot_runner.py:80`, spawn_scheduler children) all take ContextManager because auto-compact/loop-compaction middlewares own trimming (see context-auto-compact).
**Invariant:** (1) Estimate and ledger live in separate modules by design — routing heuristic counts into budget enforcement double-counts cache-discounted tokens as full price and misprices the whole run (~10–20% drift has zero cost impact ONLY while this boundary holds). (2) Eviction must skip SYSTEM messages and terminate when only system messages remain — an unguarded pop-loop either deletes the system prompt or spins. (3) `extract_text` ignores image bytes so image-only content doesn't inflate eviction pressure (test-pinned).
**Probe:** `backend/python/tests/unit/agent_loop_lib/core/test_tokens.py` (:22–71 — plain string, multipart text-parts-only, IMAGE-ONLY content extracts empty, empty-string, ~chars/4 magnitude, image bytes don't inflate count, system+user unaffected); window behavior exercised via `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_context_compaction.py` + `test_auto_compact_coverage.py`.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-pipeshub-ai","query":"count_message_tokens SlidingWindowContext ContextManager token_count","detail":"ids","limit":5}'
```

## Verdict
Adopt the 4-chars+4-overhead estimate strictly for SHAPING decisions and a separate real-usage ledger for budgets; adopt the never-evicting window wherever external summarization exists (pair it with your own compaction plane). Adapt ratios/overhead to your tokenizer family. Omit nothing. Direct-test coverage caveat: window classes have no dedicated suite — their contracts ride the compaction-middleware tests.
