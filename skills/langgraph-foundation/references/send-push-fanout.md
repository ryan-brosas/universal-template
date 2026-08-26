<!-- capsule-v2 -->
# Send PUSH fan-out — How do dynamic per-item tasks spawn, and what happens to bad packets?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** How does one `Send(node, arg)` become exactly one replay-stable task — and why does an invalid packet warn instead of crash?

## One PUSH task per TASKS-channel index; every defect path is warn-and-skip
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_algo.py:prepare_push_task_send` (:938-1107; guard block :961-1000), task-path flag :1003-1005; id derivation cross-ref `deterministic-task-ids` capsule.
**Signature:** `prepare_push_task_send(task_path: tuple[str, tuple], task_id_checksum, *, checkpoint, channels, managed, config, step, stop, for_execution, ..., parent_ns, task_id_func, processes) -> PregelTask | PregelExecutableTask | None`.
**Data Shape:** PUSH task paths are `(PUSH, idx)` with `len(task_path) == 2`; the synthetic TASKS channel accumulates `Send` packets written by any task (or `map_command`) during step N; execution reads `channels[TASKS].get() -> Sequence[Send]`.

### Decisive source
```python
    if len(task_path) == 2:
        # SEND tasks, executed in superstep n+1
        # (PUSH, idx of pending send)
        idx = cast(int, task_path[1])
        if not channels[TASKS].is_available():
            return                                  # barrier empty -> no sends this step
        sends: Sequence[Send] = channels[TASKS].get()
        if idx < 0 or idx >= len(sends):
            return                                  # stale/replayed idx -> skip
        packet = sends[idx]
        if not isinstance(packet, Send):
            logger.warning(
                f"Ignoring invalid packet type {type(packet).__name__} in pending sends")
            return
        if packet.node not in processes:
            logger.warning(f"Ignoring unknown node name {packet.node} in pending sends")
            return
        proc = processes[packet.node]
        ...
        triggers = PUSH_TRIGGER
        task_id = task_id_func(checkpoint_id_bytes, checkpoint_ns, str(step),
                               packet.node, PUSH, str(idx))
    ...
    # we append False to the task path to indicate that a call is not being made
    # so we should return interrupts from this task
    translated_task_path = (*task_path[:3], False)
```

**Flow:** Any write of a `Send` lands on the TASKS channel during apply_writes; the next superstep prepares one PUSH task per index 0..n-1. Each candidate resolves its packet, validates it (availability, bounds, type, known node), derives its deterministic id from (checkpoint id, ns, node, step, PUSH, str(idx)), builds scratchpad + Runtime override (store, previous, execution_info) plus an optional CacheKey over `cache_policy.key_func(packet.arg)` hashed with xxh3. The appended False in the translated path marks "no functional-API Call present", which `output_writes` checks (`task.path[-1] is True` suppresses only nested-call interrupts).
**Invariant:** Fan-out identity is positional — (step, node, PUSH, idx) — so resumed runs recompute identical ids and find prior pending writes; no invalid packet can fail the superstep (warn-and-skip keeps replay progressable); empty barrier simply yields zero PUSH tasks.
**Probe:** `python -m pytest "tests/test_pregel.py::test_send_sequences" "tests/test_pregel.py::test_concurrent_emit_sends" -q` (Sends as sequences + concurrent emission both fan out and join); `grep -c "Ignoring" libs/langgraph/langgraph/pregel/_algo.py` → 3 warn-and-skip paths. Secondary: `tests/test_pregel.py::test_in_one_fan_out_state_graph_waiting_edge_multiple` passes on memory/sqlite cache params; its `[redis-*]` params require a redis-server absent from this host (environmental block, recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "prepare_push_task_send Send pending sends TASKS", limit: 8 });
```

## Verdict
Adopt positional-index materialization with defensive skips — dynamic fan-out that survives crashes must not let one malformed item poison replay. Adapt the packet type/node-name validation to your host's process registry. Omit the cache-policy plumbing until you port BaseCache; the identity scheme works without it.