<!-- capsule-v2 -->
# Hook pairing exactly-once — how do EXECUTION_START/EXECUTION_END hook pairs stay balanced across success, failure, abort, and reentrant kickoffs?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What local state guarantees every start hook has at most one end hook (success or failure), never two, never zero?

## Per-invocation dispatch flags
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow.kickoff_async` :2091 — flags :2176–2191, failure pairing :2488–2493, end dispatch :2450–2460; `_dispatch_execution_end_failure` :2523–2540; resume twin `resume_async` :1338–1387 with `hook_state = {"end_dispatched": False}`).
**Signature:** `_dispatch_execution_end_failure(self, error: BaseException) -> None`.
**Data Shape:** plain locals `execution_start_dispatched: bool`, `execution_end_dispatched: bool`; resume path uses a one-key dict because the body is a separate method.

### Decisive source
```python
# Guards the failure event: everything between here and the
# ``flow_started`` emission below (hooks, input handling, state
# restore) can raise, and a ``flow_failed`` with no opener would pop
# an unrelated scope.
flow_scope_open = False
...
# Flag set before dispatching so an EXECUTION_END hook that raises
# HookAborted does not trigger a second (failure) dispatch below.
execution_end_dispatched = True
dispatch(InterceptionPoint.EXECUTION_END, end_ctx)
...
except Exception as e:
    # Pairing invariant: only fire the failure EXECUTION_END when this
    # invocation's EXECUTION_START dispatched and its EXECUTION_END has
    # not (exactly-once per invocation).
    if execution_start_dispatched and not execution_end_dispatched:
        self._dispatch_execution_end_failure(e)
```

**Flow:** kickoff sets both flags False → EXECUTION_START dispatched → flag latched True → on success, end-flag latched BEFORE dispatching EXECUTION_END (so an aborting end-hook cannot trigger the failure arm) → any exception afterwards fires the failure END only when start fired AND end has not → reentrant kickoffs share the outer usage-aggregator but keep their OWN flags ("Pairing state is local (per invocation)").
**Invariant:** At most ONE end dispatch per invocation; a HookAborted during EXECUTION_START still reads back the mutated payload, stamps state id, opens flow scope, and raises so the failure pairs with the opener. The resume path owes an END even though its START fired in the original kickoff — hence the shared `hook_state` dict threaded through `_resume_async_body`.
**Probe:** `.venv/bin/python -m pytest lib/crewai/tests/hooks/test_interception_conformance.py -q` (expect 22 passed incl. `test_no_execution_end_when_execution_start_aborts` and `test_aborting_execution_end_hook_fires_once_for_flow`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "kickoff_async execution start end hook pairing baggage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt latch-before-dispatch plus paired-failure-only-when-opened; adapt flag storage to your language's closure rules (crewAI needs a dict only to share across methods); omit baggage re-publication if you lack an INPUT interception point. Direct tests executed green at pin.
