<!-- capsule-v2 -->
# TokenUsageTracker — thread-safe per-prompt token ledger with copy-on-read

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** how does Graphiti account LLM token usage per prompt type safely under concurrency, and how does it expose an immutable snapshot for reporting?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/llm_client/token_tracker.py` (`TokenUsage`, `PromptTokenUsage`, `TokenUsageTracker`); `TokenUsageTracker.record` (:62–78), `get_usage` (:80–91), `get_total_usage` (:93–98), `reset` (:100–103), `print_summary` (:105–152).
**Signature:** `record(prompt_name: str | None, input_tokens: int, output_tokens: int) -> None`; `get_usage() -> dict[str, PromptTokenUsage]`; `get_total_usage() -> TokenUsage`.
**Data Shape:** keyed by `prompt_name` (e.g. `'extract_nodes.extract_message'`); `None` is normalized to the literal key `'unknown'`. Each `PromptTokenUsage` accumulates `call_count`/`total_input_tokens`/`total_output_tokens` and derives `total_tokens`, `avg_input_tokens`, `avg_output_tokens`. Guarded by a single `threading.Lock`.

### Decisive source
```python
def record(self, prompt_name, input_tokens, output_tokens):
    key = prompt_name or 'unknown'
        with self._lock:
            if key not in self._usage:
                self._usage[key] = PromptTokenUsage(prompt_name=key)
            self._usage[key].call_count += 1
            self._usage[key].total_input_tokens += input_tokens
            self._usage[key].total_output_tokens += output_tokens

def get_usage(self):
    with self._lock:
        return {k: PromptTokenUsage(prompt_name=v.prompt_name,
                call_count=v.call_count, total_input_tokens=v.total_input_tokens,
                total_output_tokens=v.total_output_tokens)
                for k, v in self._usage.items()}   # copy, not the live dict
```

**Flow:** `record` under the lock lazily creates the per-prompt entry then increments counters; `get_usage` returns a deep-copied dict (fresh `PromptTokenUsage` per key) so a caller mutating the returned snapshot cannot corrupt the live ledger; `get_total_usage` sums across all prompts; `reset` clears under the lock; `print_summary` sorts by a key (`total_tokens` default) and formats a fixed-width table.
**Invariant:** (1) every read/write is under the same `threading.Lock` — safe for concurrent LLM calls from multiple threads; (2) `get_usage` MUST return copies, never internal objects (the test mutates a returned entry and asserts the original is unchanged); (3) `None` prompt names collapse to `'unknown'` so uncategorized calls are still countable.
**Probe:** `tests/llm_client/test_token_tracker.py` — `test_thread_safety` (:172, 10 threads × 100 calls, exact totals), `test_concurrent_same_prompt` (:196), `test_get_usage_returns_copy` (:128, mutates returned entry, asserts original unchanged), `test_record_none_prompt_name` (:106).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "TokenUsageTracker PromptTokenUsage record get_usage threading Lock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lock-guarded per-prompt ledger + copy-on-read snapshot pattern verbatim (it is small, self-contained, and directly test-pinned); adapt the `print_summary` formatting to your reporting surface; omit if you don't need per-prompt cost attribution. The `threading.Lock` (not asyncio) is deliberate — LLM calls are thread-pooled, so keep it a plain Lock.
