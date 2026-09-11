<!-- capsule-v2 -->
# ask() timeout without orphaned threads — how does a flow block for user input yet always terminate on deadline, even when the provider ignores it?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** How do I implement a cancellable blocking input primitive over an UNCANCELLABLE provider call?

## Manual executor + shutdown(wait=False)
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow.ask` :3368–3516, timeout arm :3450–3471; auto-checkpoint `_checkpoint_state_for_ask` :3343–3365).
**Signature:** `ask(self, message: str, timeout: float | None = None, metadata: dict[str, Any] | None = None) -> str | None`.
**Data Shape:** returns the reply string; `None` on timeout/disconnect/provider error; empty string is INTENTIONAL enter-press. Every exchange appends to `_input_history` (message/response/method_name/timestamp/metadata/response_metadata).

### Decisive source
```python
# Manual executor management to avoid shutdown(wait=True)
# deadlock when the provider call outlives the timeout.
executor = ThreadPoolExecutor(max_workers=1)
ctx = contextvars.copy_context()
future = executor.submit(
    ctx.run, provider.request_input, message, cast(Any, self), metadata
)
try:
    raw = future.result(timeout=timeout)
except FuturesTimeoutError:
    future.cancel()
    raw = None
finally:
    # wait=False so we don't block if the provider is still
    # running (e.g. input() stuck waiting for user).
    executor.shutdown(wait=False, cancel_futures=True)
```

**Flow:** emit `FlowInputRequestedEvent` → best-effort state checkpoint under method name `_ask_checkpoint` so a crash while waiting stays recoverable → resolve provider (instance > global flow_config > Console) → with timeout: single-worker executor, context-copied provider call, bounded `.result(timeout)` → timeout cancels the future and abandons (NOT kills) the worker → response normalized (`InputResponse` vs str vs None), history appended, `FlowInputReceivedEvent` emitted.
**Invariant:** The provider thread may outlive `ask()` — correctness comes from returning None promptly and never joining the stuck worker (`wait=False, cancel_futures=True`); porting with plain `executor.shutdown()` deadlocks until the human types. Provider exceptions are swallowed into None (debug log); KeyboardInterrupt re-raised. Works identically inside sync methods because they already run on pool threads.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow_ask.py::TestAskTimeout::test_ask_timeout_returns_none" -q` and `"lib/crewai/tests/test_flow_ask.py::TestAskCheckpoint::test_ask_checkpoints_state_before_waiting" -q` (expect 2 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "ask input provider timeout request_input", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt abandon-don't-kill executor discipline plus pre-wait checkpointing; adapt metadata plumbing to your channels; omit input history if you don't need conversational audit. Direct tests executed green at pin.
