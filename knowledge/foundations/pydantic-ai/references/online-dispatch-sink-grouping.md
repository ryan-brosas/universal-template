<!-- capsule-v2 -->
# Online-eval dispatch — how do N evaluators sharing sinks land exactly ONE batched delivery per sink, with drops and errors routed without leaking semaphore slots?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter fanning evaluation results to multiple destinations must batch per sink, bound per-evaluator concurrency, and route every failure (drop, emission, sink, handler) to the right callback without double-firing shared handlers or leaking slots.

## Two-phase dispatch with id()-keyed sink groups
**Path/Symbol:** `pydantic_evals/pydantic_evals/_online.py:_SinkGroup/_run_and_collect/_submit_group_to_sink/dispatch_evaluators` (:295-486); `_otel_emit.py:build_parent_context` (:113-129).
**Signature:** `dispatch_evaluators(online_evaluators, context, span_reference, target, config) -> None` (async); `_run_and_collect(online_eval, context, span_reference, target, config, group) -> None`.
**Data Shape:** Groups keyed by `id()` of the RAW sink source (per-evaluator `sink=` override else `config.default_sink`) so user-visible identity drives grouping without coalescing distinct instances. `SinkPayload` is a frozen dataclass marked "do not instantiate" — fields may be added in any release; sinks read only what they need.

### Decisive source
```python
# grouping + skip-when-nowhere-to-go
raw = online_eval.sink if online_eval.sink is not None else config.default_sink
key = id(raw)
...
if not config.emit_otel_events and not sinks:
    continue          # no OTel emission AND no sinks → evaluator never runs

# phase 1, per evaluator:
if not online_eval.semaphore.acquire(blocking=False):
    if on_max_concurrency is not None:
        try: ...await on_max_concurrency(context)
        except Exception as exc: await _call_on_error(on_error, exc, ..., 'on_max_concurrency')
    return            # DROPPED — no slot, no work
parent_token = None
try:
    parent_ctx = build_parent_context(span_reference)   # NonRecordingSpan parent
    parent_token = otel_context.attach(parent_ctx) if parent_ctx is not None else None
    raw_result = await run_evaluator(evaluator, context)
    if config.emit_otel_events:
        try: emit_otel_events(results=..., failures=..., target=target, include_baggage=...)
        except Exception as exc: await _call_on_error(on_error, exc, ..., 'sink')  # 'sink' = catch-all
    group.outcomes.append((online_eval, results, failures))
finally:
    if parent_token is not None: otel_context.detach(parent_token)
    online_eval.semaphore.release()

# phase 2, per (group, sink): one flattened payload; empty batch skips submit
try: await sink.submit(payload)
except Exception as exc:
    seen = set()
    for online_eval, _, _ in group.outcomes:
        handler = online_eval.on_error if online_eval.on_error is not None else config.on_error
        if handler is None or id(handler) in seen: continue
        seen.add(id(handler))
        await _call_on_error(handler, exc, payload.context, online_eval.evaluator, 'sink')
```

**Flow:** group by raw sink source id → drop groups whose results would have nowhere to go (`emit_otel_events=False` and no sinks) → phase 1 runs every evaluator in parallel under an anyio task group, each behind a non-blocking semaphore acquire (drop → `on_max_concurrency`, whose own exceptions route to `on_error('on_max_concurrency')`), with the call span attached as OTel parent for the whole evaluator run → outcomes stashed on the group → phase 2 flattens each group's outcomes into ONE `SinkPayload` per sink, submitted in parallel; empty batches (no results AND no failures) skip submit entirely.
**Invariant:** Exactly one `submit` per (group, sink) per call, and a shared `on_error` handler fires exactly ONCE per sink failure (dedup by `id(handler)`). The semaphore release must survive attach/emission failures — hence the acquire-paired try/finally with parent-context setup INSIDE the try. `'sink'` is deliberately the catch-all error location covering both custom sinks and default OTel emission.
**Probe:** `tests/evals/test_online.py::test_shared_on_error_across_evaluators_fires_once_per_sink_failure` (:1187-1215) pins `fires == ['sink']` for two evaluators sharing one failing sink; `test_dispatch_skipped_when_emit_off_and_no_sinks` (:2353-2369) pins the short-circuit (call span exists, no `evaluator:` span, no log events); `test_max_concurrency_respected` (:892-924) pins `max_active <= 2` under `max_concurrency=2`; `test_evaluator_returning_empty_mapping_emits_nothing` (:1219-1237) pins the empty-batch skip.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "dispatch_evaluators _SinkGroup _run_and_collect semaphore", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session; anchors confirmed by direct read of _online.py :295-486 and _otel_emit.py :113-129 at pin `a5b5fb7a`.

## Verdict
Adopt the two-phase shape (parallel collect, then batched fan-out) and the id()-keyed grouping — it is what makes "evaluators sharing a sink get one delivery" true without identity semantics on sink objects. Adopt the non-blocking acquire + drop-callback pattern and the acquire-paired finally. Adapt the `OnErrorLocation` vocabulary to your host's error taxonomy but keep ONE catch-all location for downstream delivery. Omit the OTel parent attach/detach sandwich unless your host has a span model — its only job is nesting the evaluator span under the call span. Coverage caveat: none — file read whole this pass.
