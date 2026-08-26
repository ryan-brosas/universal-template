<!-- capsule-v2 -->
# Dynamic batch warmup — how is the first-minute export experience made responsive without permanently lowering batching efficiency?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** How does the SDK get the first ~10 spans exported near-instantly while settling to the standard schedule afterwards?

## DynamicBatchSpanProcessor
**Path/Symbol:** `logfire/_internal/exporters/dynamic_batch.py:DynamicBatchSpanProcessor.on_end` (`dynamic_batch.py:29-33`).
**Signature:** `__init__(self, exporter: SpanExporter)`; mutates `processor._batch_processor._schedule_delay` through property shims.
**Data Shape:** initial delay `min(final_delay, 100)` ms where `final_delay = float(os.environ.get('OTEL_BSP_SCHEDULE_DELAY') or 500)`; flip trigger exactly at `num_processed == 10`.

### Decisive source
```python
self.final_delay = float(os.environ.get(OTEL_BSP_SCHEDULE_DELAY) or 500)
# Start with the configured value immediately if it's less than 100ms.
initial_delay = min(self.final_delay, 100)
...
def on_end(self, span: ReadableSpan) -> None:
    self.num_processed += 1
    if self.num_processed == 10:
        self.schedule_delay_millis = self.final_delay
    super().on_end(span)
```

**Flow:** construct inner `BatchSpanProcessor(schedule_delay_millis=100)` → each ended span increments the counter → on exactly the 10th, rewrite the private `_schedule_delay` to the env-configured final (default 500ms) → subsequent batches use normal cadence.
**Invariant:** The `== 10` equality (not `>=`) is safe because the counter monotonically increases and the condition is checked before every delegation; using `>=` would be equally correct but `==` documents one-shot intent. If OTEL_BSP_SCHEDULE_DELAY is already <100ms there is no warmup phase — `min()` collapses both phases. This reaches INTO OTEL privates (`_batch_processor._exporter`, `_schedule_delay`), which is pinned by tests so OTEL upgrades that move these attrs break loudly.
**Probe:** `tests/test_processor_wrapper.py` / test_configure batch-exporter fixtures — assert the delay transition after 10 spans.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "DynamicBatchSpanProcessor schedule_delay_millis OTEL_BSP_SCHEDULE_DELAY", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the warmup-then-settle pattern for any batched pipeline where early feedback matters (dev experience). Adapt the trigger count and delays to your domain. Omit the OTEL-private attribute reach-through if your batch processor exposes a public knob.
