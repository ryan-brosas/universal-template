<!-- capsule-v2 -->
# Tail-sampling buffer FSM — how are whole traces buffered, decided, and replayed to deferred processors?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What is buffered on start vs end, when does the decision fire, and what replay does each processor class get?

## TailSamplingProcessor
**Path/Symbol:** `logfire/sampling/_tail_sampling.py:TailSamplingProcessor` (`_tail_sampling.py:147-286`).
**Signature:** `__init__(processor: SpanProcessor, get_tail_sample_rate: Callable[[TailSamplingSpanInfo], float], deferred_processor: SpanProcessor | None)`; `SamplingOptions.level_or_duration(*, head, level_threshold='notice', duration_threshold=5.0, background_rate=0.0)` builds the standard callback.
**Data Shape:** `self.traces: dict[trace_id, TraceBuffer{started: list[(Span, Context)], ended: list[ReadableSpan], first_span: Span}]` under one Lock; duration measured from buffer's FIRST span start.

### Decisive source
```python
# on_start: main processor called IMMEDIATELY (outside the lock);
# only deferred processor waits for the decision.
with self.lock:
    if span.parent is None:
        self.traces[trace_id] = TraceBuffer(started=[], ended=[], first_span=span)
    buffer = self.traces.get(trace_id)
    if buffer is not None:
        if self.deferred_processor is not None:
            buffer.started.append((span, parent_context))
        dropped = self.check_span(...)
super().on_start(span, parent_context)   # comment: most processors just set attributes,
                                         # which is safe before the sampling decision
...
# on_end: buffered for BOTH processors.
if buffer is not None:
    buffer.ended.append(span)
    dropped = self.check_span(...)
    if span.parent is None:
        self.traces.pop(trace_id, None)   # root ended -> trace hopefully complete; free memory
...
def check_span(self, span_info) -> bool:
    sample_rate = self.get_tail_sample_rate(span_info)
    if sampled := check_trace_id_ratio(span_info.buffer.trace_id, sample_rate):
        self.drop_buffer(span_info.buffer)
    return sampled
```
Replay (`push_buffer`): deferred processor gets BOTH started-replay and ended-replay; main gets ONLY ended ("on_start was already called immediately"). Decision uses trace-id-ratio against the BUFFER's trace_id so any single hot span includes the whole trace. Shutdown/flush wrap the deferred processor in `suppress_instrumentation()` — "prevents the deferred processor (e.g. PendingSpanProcessor) from creating new spans during shutdown, which would re-enter this processor and cause infinite recursion."
**Flow:** root starts → buffer created → each start checks callback (level≥threshold or cumulative-duration>threshold ⇒ rate 1.0 else background_rate) → hit ⇒ drop buffer + push (spans arriving later flow straight through since no buffer) → no hit and root ends ⇒ buffer discarded silently. No-buffer spans pass through instantly to both processors.
**Invariant:** The lock must NOT be held while calling wrapped processors (explicit comments — user processors "might do anything"). `tail_sampling_defer_on_start=True` class attribute opts arbitrary user processors into deferral. Memory warning: every span of unsampled traces is retained until completion.
**Probe:** `tests/test_tail_sampling.py` (incl. TestSampler harness at :358-370) — pins inclusion thresholds and replay order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "TailSamplingProcessor TraceBuffer push_buffer level_or_duration", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: split immediate-vs-deferred processor classes, lock-never-around-callbacks discipline, root-end cleanup, suppression-guarded shutdown replay. Adapt threshold semantics to your SLOs. Omit the deferred channel if you ship no start-side-effecting processors.
