<!-- capsule-v2 -->
# _ContinuationStreamedResponse — how do continuation segments present as ONE stream with correct indices, usage, and cancel semantics?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does a composite streamed response re-emit per-segment events with non-colliding part indices while preserving live usage snapshots and distinguishing detach from cancel?

## Segment-stitching composite
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/_continuation.py:_ContinuationStreamedResponse` (:237-628): `__aiter__` (:282), `_get_event_iterator` (:368-474), `_segment_offset` (:476-498), `_snapshot`/`usage` (:505-523), `get()` (:525-553), `close_stream` (:555), `aclose` (:567).
**Signature:** dataclass taking model/settings/base_messages/run_context/two ceilings/sleep_func/check_usage/finalize_response + optional `initial_suspended_response`; `segment_context()` re-attaches ambient spans around lazily-opened segments.
**Data Shape:** Emits fully-formed `PartStart/PartDelta/PartEnd` + `FinalResultEvent`s (each sub-stream is already wrapped by the base helpers; the composite adds ONLY reindexing, final-result capture, and the cancel-guard).

### Decisive source
```python
# _continuation.py:476-498 — reindex offset SHARES merge_mode's decision so live event
# indices match the eventual merge exactly
def _segment_offset(response, sub, last_segment_offset):
    if response is None: return 0
    mode = merge_mode(response, sub.get())     # resolved LAZILY on first reindexable event,
    if mode == 'accumulate':                   # once sub.provider_response_id is populated
        return len(response.parts)             # append after all prior parts
    if mode == 'replace-new':
        return 0                               # prior response superseded; restart index space
    return last_segment_offset                 # replace-same-id re-emits same parts in place

# :461-468 — a later segment failing with a suspended job in hand cancels the server-side
# job (mirrors the non-streaming loop) so history never records an unresumable job
except BaseException:
    if response is not None and response.state == 'suspended' and not (self._cancelled or self._stopped):
        await cancel_suspended_job(self.model, response)
    raise

# :540-549 — get() state machine: detach (aclose WITHOUT cancel) leaves a still-pending
# job resumable 'suspended'; a real cancel() killed it → non-resumable 'interrupted'
if self._finished:            state = 'complete'
elif self._cancelled:         state = 'interrupted'
elif self._detached and snapshot is not None and snapshot.state == 'suspended':
                              state = 'suspended'
else:                         state = 'incomplete'
```

**Flow:** loop { cancelled? break → count re-suspension against the ceiling picked by `last_mode` → sleep `model.continuation_delay(response)` then RE-CHECK cancellation before opening the next sub-stream (a cancel during the sleep tore down the job; opening another segment for `pause_turn` would actively resume generation and burn tokens) → open segment inside `segment_context()`, reindex each event by the resolved offset, capture `FinalResultEvent` → after the `async with` exits read `sub.get()` (late-stamped metadata captured) → finalize BOTH segments' usage separately (per-request pricing preserved incl. tiers) → classify transition into `last_mode`, merge → refresh `_usage`, run `check_usage` }. `usage` property folds the in-flight sub's live snapshot over the committed accumulator (`_merged_response` excludes the current sub to avoid double counting). Between-segment sleeps use injected `sleep_func` so durable executors replay deterministically. `aclose()` closes the INNER generator directly (the outer guard's `async for` doesn't forward aclose — segments' connections would leak until GC); suppresses only `is_async_generator_already_running` RuntimeError from parked prefetch tasks. Known accepted gap: `PartEndEvent.next_part_kind` is None at segment boundaries (parts never merge across boundaries).

**Invariant:** Live event indices must equal final merged-response indices for every mode (offset decision = merge decision, same function). Usage is finalized per segment BEFORE merging and checked on every merge. Detach ≠ cancel: only `cancel()/close_stream()` kills the server-side job (`close_stream` cancels even if connection teardown raised); `aclose()` alone records `'suspended'`.

**Probe:** `tests/models/test_streamed_continuation.py::test_streamed_accumulate_offsets_part_indices` (:251), `::test_replace_poll_chain_runs_past_max_generation_continuations` (:864), `::test_cancel_during_between_segment_sleep_skips_next_request` (:1165), `::test_detach_records_suspended_when_job_pending` (:1044); agent-level `tests/models/test_streamed_continuation.py::test_run_stream_early_break_records_suspended_and_resumes` (:1090).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_ContinuationStreamedResponse _segment_offset cancel_suspended_job close_stream", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared-decision reindexing, post-sleep cancel re-check, per-segment finalize-before-merge, and the three-way get() state machine with detach-vs-cancel. Adapt `segment_context` to your host's tracing. Omit the prefetch-race suppression only if your consumer stack cannot park mid-generator. Coverage clean at the pinned commit.
