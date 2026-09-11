<!-- capsule-v2 -->
# Streamed response state machine — which lifecycle state does a finished-or-killed stream report, and who wins?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When iteration ends by exhaustion, early break, aclose(), or cancel() — how does `StreamedResponse.get()` decide between complete/incomplete/interrupted/suspended?

## `StreamedResponse.__aiter__` iterator stack + `_finished`/`_cancelled` + `get()` precedence
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/__init__.py:iterator_with_cancel_guard` (:1046–1075), `cancel()` (:1082–1097), `get()` state ladder (:1137–1165), `time_to_first_chunk` (:1201–1211); state literals in messages.py `ModelResponseState` (:126).
**Signature:** `async def cancel(self) -> None`; `def get(self) -> ModelResponse`; guard composes `iterator_with_cancel_guard(iterator_with_part_end(iterator_with_final_event(inner)))`.
**Data Shape:** Two booleans decide derived states: `_cancelled` (explicit `cancel()` called) and `_finished` (iteration drained to natural StopAsyncIteration without cancellation). Provider-stamped `self.state` ('suspended'/'incomplete') is the third input.

### Decisive source
```python
# models/__init__.py:1144-1152 — suspended > complete > interrupted > incomplete
if self.state == 'suspended':
    state = 'suspended'
elif self._finished and self.state != 'incomplete':
    state = 'complete'
elif self._cancelled:
    state = 'interrupted'
else:
    state = 'incomplete'

# :1062-1075 — ONLY natural StopAsyncIteration on an uncancelled stream sets _finished
else:
    if not self._cancelled:
        self._finished = True
```

**Flow:** transport errors raised by `cancel()` tearing down the connection are SUPPRESSED inside the guard iff `self.cancelled` (otherwise re-raised — real failures stay loud). Early `break`/`aclose()` raise GeneratorExit at the suspended yield → no else-branch → stays 'incomplete'. A defensive `cancel()` AFTER natural completion leaves `_finished=True` (set before `_cancelled` could matter) so 'complete' survives. A cancel mid-stream that still drains naturally (local model, no live connection): `_cancelled` wins over `_finished` → 'interrupted'.

**Invariant:** Provider 'suspended' is the one state `get()` can't derive, so it outranks everything. An explicit in-flight 'incomplete' hint from the provider beats natural completion (foreground OpenAI Responses stream EOF'd without terminal event). `_cancelled` outranks that hint. Never stamp 'complete' unless iteration truly drained uncancelled — silent completeness of a truncated stream is the failure mode this whole machine exists to prevent.

**Probe:** `tests/test_streaming.py::test_run_stream_cancel` (:6389, cancel→interrupted), `test_run_stream_cancel_guard_suppresses_transport_error` (:6420, suppressed teardown), `test_run_stream_cancel_after_complete` (:6452, defensive late cancel keeps complete), `test_testmodel_stream_cancel_reports_interrupted` (:6476), `test_stream_cancel_with_natural_drain_reports_interrupted` (:6500, drain-but-cancelled), `test_stream_response_state_incomplete_until_finished` (:6889) + `..._after_early_break` (:6912).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "iterator_with_cancel_guard StreamedResponse get _finished _cancelled time_to_first_chunk", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-input precedence (provider-suspended > finished-uncancelled-complete > cancelled-interrupted > incomplete) and the suppress-only-if-we-cancelled error guard. Adapt error tuples via `get_stream_cancel_errors()` per transport (httpx default; gRPC/botocore override). Omit the PartEnd-injection and FinalResultEvent layers (covered by existing capsules' neighbors) — they compose orthogonally.
