<!-- capsule-v2 -->
# Deterministic task IDs — How do writes find their task after a crash and restart?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** How is a task's identity derived so that checkpointed pending writes, resume values, and cache entries match after re-execution?

## Task id = hash(checkpoint_id, ns, step, name, PULL/PUSH, triggers)
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_algo.py:prepare_single_task` (:524-761; id derivation :553-561), hash selector :550.
**Signature:** `task_id = task_id_func(checkpoint_id_bytes, checkpoint_ns, str(step), name, PULL|PUSH, *triggers)` where `task_id_func = _xxhash_str if checkpoint["v"] > 1 else _uuid5_str`.
**Data Shape:** PULL tasks: `(PULL, node_name)` paths, triggers = sorted node trigger channels. PUSH tasks (`prepare_push_task_send` :938): `(PUSH, idx)` into the TASKS channel of Send packets, triggers = `PUSH_TRIGGER`, id includes `str(idx)`. Functional-API calls: `(PUSH, path, write_idx, task_id, Call)` via `prepare_push_task_functional`. Task namespace: `{parent_ns}|{name}:{task_id}`.

### Decisive source
```python
if _triggers(channels, checkpoint["channel_versions"], ...):
    triggers = tuple(sorted(proc.triggers))
    checkpoint_ns = f"{parent_ns}{NS_SEP}{name}" if parent_ns else name
    task_id = task_id_func(
        checkpoint_id_bytes, checkpoint_ns, str(step), name, PULL, *triggers,
    )
```
**Flow:** Same checkpoint + same step + same node + same triggers ⇒ same id on replay. That id keys the scratchpad (resume lookup by `(task_id, RESUME)`), `put_writes(task_id, ...)` dedupe (existing writes for the task are REPLACED), cache lookups (`CacheKey((CACHE_NS_WRITES, identifier, name), xxh3(args_key))`), and error attribution. Checkpoint v1 graphs use uuid5; v4 (LATEST_VERSION) uses xxh3-128 — both deterministic; the switch is per-checkpoint-version so old threads keep their ids stable across migration.

**Invariant:** NEVER add wall-clock or randomness to task identity — resume, retry-cache, and write-replacement all assume byte-stable ids within one checkpoint lineage. `accept_push` reuses the identical derivation for mid-step PUSH tasks so their writes persist under the same key they'd regenerate from.

**Probe:** `grep -n '_xxhash_str if checkpoint' libs/langgraph/langgraph/pregel/_algo.py` → 2 hits (:550, :1138); `grep -n 'PUSH_TRIGGER' libs/langgraph/langgraph/pregel/_algo.py | head -2`. Direct tests: `tests/test_retry.py:702 test_send_timeout_round_trips_through_msgpack_serde` (identity survives serde); interrupt-resume suites in test_pregel.py exercise id-matched resume writes end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "prepare_single_task", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt content-derived task identity as the keystone of resumability. Adapt the hash (xxh3 vs uuid5) and namespace grammar to your host; keep derivation pure in checkpoint state. Omit the v1-compat branch only when your store has no legacy checkpoints.
