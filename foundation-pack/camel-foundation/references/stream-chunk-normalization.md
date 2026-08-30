<!-- capsule-v2 -->
# Stream chunk normalization ladder — How do per-worker token streams become a single coherent user-facing stream?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** How are accumulate-mode chunks diffed into deltas, keyed, and cleaned up without cross-task bleed?

## stream_id-keyed progress map with final-chunk cleanup
**Path/Symbol:** `camel/societies/workforce/workforce.py:Workforce._on_worker_stream_chunk` (:628-658), `_extract_stream_chunk` (:1270), `_clear_stream_progress_if_final` (:1329).
**Signature:** `_on_worker_stream_chunk(chunk, worker_id, task_id)`; user callback shape `(worker_id, task_id, text, stream_accumulate_mode)`.
**Data Shape:** `_stream_progress: Dict[Tuple[str, str], str]` keyed `("stream", f"{worker_id}:{task_id}")`; mode read via fallback chain `chunk.info.get("stream_accumulate_mode", chunk.info.get("mode", "accumulate"))`, validated against `{"delta","accumulate"}` (:1284-1289).

### Decisive source
```python
stream_id = f"{worker_id}:{task_id}"
stream_payload = self._extract_stream_chunk(chunk, stream_id=stream_id)
...
text, stream_accumulate_mode = stream_payload
self._emit_stream_chunk_event(text=..., task_id=task_id, worker_id=worker_id)
if self._user_stream_callback is not None:
    maybe = self._user_stream_callback(worker_id, task_id, text, stream_accumulate_mode)
    if asyncio.iscoroutine(maybe): await maybe
finally:
    self._clear_stream_progress_if_final(chunk, stream_id)   # ALWAYS runs
```

**Flow:** worker-side `_process_single_task` wraps the raw callback so exceptions are logged-and-swallowed (a broken UI sink can't fail the task — pinned by test `test_worker_stream_callback_exception_does_not_fail_task`); workforce-side accumulates prior text per progress_key and, in `"accumulate"` mode (full text each time), emits the DIFF when new content startswith the stored prefix — a non-prefix continuation falls back to emitting the WHOLE content rather than a negative slice (:1298-1300); delta chunks pass through; empty diffs emit NOTHING (`return None` :1306). Final-chunk cleanup pops the key only when `chunk.terminated` or `info["partial"] is False` (`_clear_stream_progress_if_final` :1329-1339). The same machinery serves internal decomposition streams under the literal stream_id `"internal"` (:1345). Direct test `test_workforce_stream_callback_accumulate_mode_emits_delta` pins "Hello" then " world".
**Invariant:** The progress map MUST be keyed per stream and cleared on final chunks — keying by either worker or task alone collides across concurrent tasks; leaking entries corrupts every later diff for that pair. Callback failures are contained at BOTH layers.
**Probe:** `grep -c 'test_worker_stream_callback_exception_does_not_fail_task' test/workforce/test_workforce_single_agent.py` → 1 hit at :210; `grep -c 'progress_key' camel/societies/workforce/workforce.py` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "_on_worker_stream_chunk _stream_progress _extract_stream_chunk", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pair-keyed progress + diff-on-accumulate + finally-cleanup + exception-swallowing callbacks as one unit — they only work together. Adapt event shapes to your transport. Omit WorkforceEvent pydantic models if you emit directly.
