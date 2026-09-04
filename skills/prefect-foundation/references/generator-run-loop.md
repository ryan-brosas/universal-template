<!-- capsule-v2 -->

# Generator run loop with GeneratorExit commit — Who finalizes the engine when the consumer abandons a generator mid-stream?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** How do you drive an engine around a user generator so both exhaustion AND abandonment reach handle_success?

## StopIteration success / GeneratorExit success(None) / rethrow

**Path/Symbol:** `src/prefect/flow_engine.py:run_generator_flow_sync (2098-2136)`; async twin `2139-2180`; task twins in `src/prefect/task_engine.py:1721-1779` (sync) and `1782-1841` (async); dispatcher `run_flow (:2182-2226)` picks by `flow.isasync`/`flow.isgenerator`.

**Signature:** `run_generator_flow_sync(flow, flow_run=None, parameters=None, wait_for=None, return_type="result", context=None) -> Generator[R, None, None]` (raises ValueError if `return_type != "result"`).

**Data Shape:** Each yielded item passes through `link_state_to_flow_run_result(engine.state, gen_result)` before reaching the consumer, so dependency tracking sees partial results.

### Decisive source
```python
try:
    while True:
        gen_result = next(gen)
        # link the current state to the result for dependency tracking
        link_state_to_flow_run_result(engine.state, gen_result)
        yield gen_result
except StopIteration as exc:
    engine.handle_success(exc.value)
except GeneratorExit as exc:
    engine.handle_success(None)
    gen.throw(exc)
```

**Flow:** outer shell `with engine.start(): while engine.is_running(): with engine.run_context(): ...` — the while-loop re-enters run_context on retries/scheduled deferrals · generator driven by `next()` per item · StopIteration(.value) ⇒ normal completion with return value · consumer closes early ⇒ GeneratorExit ⇒ finalize with result None THEN `gen.throw(exc)` to propagate close into the user generator's own finally blocks.

**Invariant:** (1) Abandonment must still produce a terminal engine outcome (`handle_success(None)`) — skipping it leaves the run non-final forever. (2) The rethrow order matters: finalize FIRST (state writes), then throw into the user generator so ITS cleanup runs under an already-terminal engine. (3) Task-engine twins additionally guard the committed-txn read path with `if False and txn.is_committed():` — an explicitly-disabled branch documenting that generators must NOT serve cached reads ("generators should default to commit_mode=OFF because they are dynamic by definition"). (4) Async generator variant raises failures at the END (`if engine.state.is_failed(): await engine.result()`) because async gens cannot return values.

**Probe:** `grep -cF 'while engine.is_running():' src/prefect/flow_engine.py` → 4 (sync/async × plain/generator shells); `grep -cF 'link_state_to_flow_run_result(engine.state, gen_result)' src/prefect/flow_engine.py` → 2. Direct tests: `tests/test_flow_engine.py:2651 TestDriveRunFlowResult.test_consumes_generators`, `:2665 test_does_not_consume_generator_returned_by_sync_non_generator_flow`; engine-level `tests/test_flow_engine.py:4461 test_generator_flow`, `:4477 test_generator_flow_requires_return_type_result`, `:4510 test_generator_flow_with_return`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "run_generator_flow_sync StopIteration GeneratorExit", "limit": 3}'
```

## Verdict
Adopt the exhaustion-vs-abandonment pairing whenever wrapping user generators in lifecycle machinery; adapt the result-linking mechanism; omit Prefect's state-proposal details inside handle_success.
