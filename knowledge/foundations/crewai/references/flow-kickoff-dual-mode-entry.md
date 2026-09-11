<!-- capsule-v2 -->
# Flow kickoff dual-mode entry — nested-loop escape, restore/fork, and the exactly-once failure pairing ladder

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How does sync `kickoff()` survive a running event loop, how do `inputs["id"]` / `restore_from_state_id` / `from_checkpoint` differ, and which events must pair on every exit path?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` — `kickoff` (:2026), `kickoff_async` (:2091) with pairing flags :2178-2184 and finally ladder :2495-2521.
**Signature:** `kickoff(inputs=None, input_files=None, from_checkpoint: CheckpointConfig | None = None, restore_from_state_id: str | None = None) -> Any | StreamSession`; `async kickoff_async(...) -> Any | AsyncStreamSession`.
**Data Shape:** inputs doubles as resume key carrier (`{"id": uuid}`); per-invocation locals `execution_start_dispatched` / `execution_end_dispatched` / `flow_scope_open` make reentrant kickoffs on ONE instance independent.

### Decisive source
```python
# :2082 — nested-loop escape: run asyncio.run in a fresh thread WITH copied context
try:
    asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(ctx.run, asyncio.run, _run_flow()).result()
except RuntimeError:
    return asyncio.run(_run_flow())

# :2055 — two restoration systems are mutually exclusive BY CONTRACT
if from_checkpoint is not None and restore_from_state_id is not None:
    raise ValueError("Cannot combine `from_checkpoint` and `restore_from_state_id`. "
        "These parameters target different state systems "
        "(Checkpointing and @persist) and cannot be used together.")

# :2270 fork mints a NEW persistence key so source history stays intact
new_state_id = (inputs.get("id") if inputs else None) or str(uuid4())
self._stamp_state_id(new_state_id)

# :2244 resumption flag only when there are completed methods to replay —
# "the flag would incorrectly suppress cyclic re-execution" otherwise
if self._completed_methods:
    self._is_execution_resuming = True

# :2486 except-handler pairs failures exactly once per invocation
except Exception as e:
    if execution_start_dispatched and not execution_end_dispatched:
        self._dispatch_execution_end_failure(e)
    if flow_scope_open:
        await self._emit_flow_failed(e)
    raise
```

**Flow:** validate mutual exclusion → checkpoint restore short-circuits into a restored instance's kickoff → stream mode returns session instead of running → set OTel baggage (`flow_inputs`) + contextvar tokens (id/name/request-id; only when unset — reentrancy) → EXECUTION_START + INPUT hooks (payload aliasing means in-place hook edits survive; HookAborted path stamps id, opens scope, re-raises so failure pairs with opener) → republish baggage AFTER hooks → reset-vs-restore bookkeeping → fork hydration → conditional/unconditional start selection (conditional starts run at kickoff ONLY when no unconditional starts exist) → starts sequential or gathered → OUTPUT → EXECUTION_END → drain event futures → memory-write drain → FlowFinishedEvent (+trace finalize unless deferred).
**Invariant:** `flow_failed` may only fire when this invocation opened the scope (`flow_scope_open`) — a failure before `flow_started` would pop an unrelated scope. `from_checkpoint`/`restore_from_state_id` raise rather than silently pick one system. Fork = hydrate old state + fresh state.id; restore-by-id = same persistence key continues.
**Probe:** `grep -c 'Cannot combine' lib/crewai/src/crewai/flow/runtime/__init__.py` → `2`; `grep -c 'pool.submit(ctx.run, asyncio.run' lib/crewai/src/crewai/flow/runtime/__init__.py` → `1`.
**Direct test:** `tests/test_flow_persistence.py::test_fork_with_restore_from_state_id` (:239) + `::test_fork_with_pinned_state_id` (:279); `tests/test_flow.py::test_cyclic_flow_works_with_persist_and_id_input` (:2077).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "Flow.kickoff synchronous context stream_events restore_from_state_id", limit: 5 });
// → ext-crewAI.lib.crewai.src.crewai.flow.runtime.Flow.stream_events Method 1960-1991; tests ...test_fork_with_restore_from_state_id Function 239-276
```

## Verdict
Adopt the nested-loop escape, the two-restoration-systems ValueError boundary, fork-mints-new-key rule, and exactly-once failure pairing. Adapt hook/baggage names. Omit trace-batch finalization internals (product telemetry).
