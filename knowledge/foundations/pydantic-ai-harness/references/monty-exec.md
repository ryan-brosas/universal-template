<!-- capsule-v2 -->
# MontyExecutor — a synchronous-snapshot REPL driver that dispatches external calls to a host callback across three execution modes

**Source:** pydantic-ai-harness (MIT) `main@c79fabc58fd3bd587dcc27f9e7d9de179d748cf0`; Codebase Memory `pydantic-ai-harness`. **Question:** how does a code-execution capability drive a Monty REPL to completion, dispatching sandboxed external function calls back to the host (tools or sub-agents) without a background async adapter?

## MontyExecutor
**Path/Symbol:** `pydantic_ai_harness/_monty_exec.py` — `MontyExecutor`, `DispatchFn`, `MontyState`, `PrintCapture`, `is_sandbox_panic`; consumers `code_mode/_capability.py`, `dynamic_workflow/_capability.py`.
**Signature:** `MontyExecutor(dispatch: DispatchFn, valid_names: Container[str], sequential_names: set[str] = set(), global_sequential: bool = False)`; `async run(state: MontyState) -> MontyComplete`. `DispatchFn = Callable[[str, dict[str, Any]], Coroutine[Any, Any, Any]]`.
**Data Shape:** single-use — accumulates per-run state in `_pending`/`_pre_resolved`, so construct a fresh executor per `run`, never reuse/share across concurrent runs. Uses the synchronous snapshot API (`feed_start`/`resume`) rather than `AsyncMonty`, deliberately: each suspension is exposed to this host-controlled loop without a background async adapter; under Temporal the loop runs workflow-side and replays.

### Decisive source
```python
# External calls are handled by execution mode:
# - Parallel (async def): deferred via resume({'future': ...}) and eagerly
#   scheduled as asyncio.Task; resolved at FutureSnapshot via asyncio.gather.
# - Per-call sequential (def, name in sequential_names): resolved inline at
#   FunctionSnapshot; any pending parallel tasks are awaited first (barrier).
# - Global sequential: all calls deferred but stored as bare coroutines and
#   awaited one-at-a-time to prevent interleaving.
# is_sandbox_panic: pyo3 raises pyo3_runtime.PanicException, a BaseException
# (not Exception) from a module that cannot be imported, so it is matched by
# name -- callers convert it to a retry rather than tearing down the run.
```

**Flow:** `run` loops over snapshots: `NameLookupSnapshot` → `resume()` (leave name undefined so sandbox raises `NameError`); `FunctionSnapshot` → `_handle_function` (dispatch per mode); `FutureSnapshot` → `_resolve_futures` (gather parallel). `PrintCapture` collects bounded print output and `prepend_to` prefixes captured stdout to an error message so the model sees what printed before the error.
**Invariant:** single-use executor; the synchronous-snapshot API keeps each suspension host-controlled and Temporal-replayable; sandbox panics are retried, never fatal.
**Probe:** `tests/code_mode/test_code_mode.py`, `test_dbos.py`, `test_temporal.py` and `tests/dynamic_workflow/test_dynamic_workflow.py` pin the three execution modes, dispatch, and panic handling.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "MontyExecutor FunctionSnapshot FutureSnapshot dispatch is_sandbox_panic", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the synchronous-snapshot driver with the three execution modes and panic-as-retry; adapt the dispatch callback to the host's tool/sub-agent surface; omit host-specific Monty/Temporal wiring.
