<!-- capsule-v2 -->
# Direct imperative model API + instruction bridging

## Source / Question
`pydantic_ai_slim/pydantic_ai/direct.py` — How does the imperative "direct" API make model requests with minimal abstraction, and how does it bridge `instructions` (on `ModelRequest`) to `instruction_parts` (on `ModelRequestParameters`) for models that read them directly? A porter must know the sync/async surface and the instruction bridge.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/direct.py` — `_ensure_instruction_parts` (34–52), `model_request` (55–106), `model_request_sync` (108–162), `model_request_stream` (164–225), `model_request_stream_sync` (227–~400), `StreamedResponseSync` (317–~400).

## Signature
```python
async def model_request(model, messages, *, model_settings=None, model_request_parameters=None, instrument=None) -> ModelResponse
def model_request_sync(model, messages, *, ...) -> ModelResponse
async def model_request_stream(model, messages, *, ...) -> AsyncIterator[StreamedResponse]
def model_request_stream_sync(model, messages, *, ...) -> Iterator[StreamedResponse]
```

## Data Shape
`ModelRequestParameters` carries `instruction_parts: list[InstructionPart] | None`. `ModelRequest` carries `instructions: str | None`. `SyncStreamBridge` bridges the async stream CM to sync.

## Decisive source
`_ensure_instruction_parts` (34–52): if `instruction_parts` is already set, return unchanged. Otherwise scan `reversed(msgs)` for the first `ModelRequest` with non-None `instructions` and `dataclasses.replace` a new `ModelRequestParameters` with `instruction_parts=[InstructionPart(content=...)]`. `model_request` (55–106) then calls `model_instance.request(list(messages), model_settings, mrp)`.

## Flow / Invariant
1. **Thin wrapper**: the direct API is only input/output schema translation around `Model` implementations — no agent graph, no tool execution.
2. **Instruction bridge**: users set `instructions` on `ModelRequest` but may not set `instruction_parts` on `ModelRequestParameters`; the bridge fills the gap so models reading `instruction_parts` directly still see the instructions. Only the LAST request's instructions are used (reverse scan, first match).
3. **Sync surface** (`model_request_sync`) wraps `model_request` with `loop.run_until_complete(...)` — cannot be used inside async code or with an active event loop.
4. **Stream sync surface** (`model_request_stream_sync`) uses `SyncStreamBridge` to keep the async CM on the caller's event loop (see `sync-stream-bridge.md`).
5. `instrument` param: `None` defers to `logfire.instrument_pydantic_ai`; `True`/settings wrap via `instrument_model`.

## Probe (direct test)
`tests/test_direct.py` (305L) + `tests/test_sync_stream_loop_affinity.py` (direct surface parametrization, :132/:133).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'model_request direct'` → `direct.model_request` (55–106), `_ensure_instruction_parts` (34–52).

## Verdict
**Adopt** the instruction-bridge pattern (reverse-scan `ModelRequest.instructions` → `instruction_parts`) — a reusable gap-filler for any host where instructions live on the message but the model reads them from request parameters. The sync surfaces are thin and host-specific.
