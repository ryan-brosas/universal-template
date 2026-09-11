<!-- capsule-v2 -->
# Version-based trigger algebra — How does a node decide it should run in the next superstep?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** What exact ordering of consume/update/bump_step/finish makes triggers fire exactly once per state change?

## apply_writes is the only place versions move
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_algo.py:apply_writes` (:232-345), `_triggers` (:1260-1279), `should_interrupt` (:155-186).
**Signature:** `apply_writes(checkpoint, channels, tasks, get_next_version, trigger_to_nodes) -> set[str]`.
**Data Shape:** checkpoint dict carries `channel_versions` (per-channel monotonically increasing version, default int via `increment`) and `versions_seen` (per-task name → channel → last version seen). `trigger_to_nodes` maps channel → nodes subscribed.

### Decisive source
```python
# sort tasks on path, to ensure deterministic order for update application
tasks = sorted(tasks, key=lambda t: task_path_str(t.path[:3]))
bump_step = any(t.triggers for t in tasks)
# 1) record versions_seen for every triggered channel of every task
# 2) compute next_version = get_next_version(max(channel_versions.values()), None)
# 3) CONSUME all channels that were read:
for chan in {chan for task in tasks for chan in task.triggers
             if chan not in RESERVED and chan in channels}:
    if channels[chan].consume() and next_version is not None:
        checkpoint["channel_versions"][chan] = next_version
# 4) group writes by channel and apply; updated+available channels trigger:
    if channels[chan].update(vals) and next_version is not None:
        checkpoint["channel_versions"][chan] = next_version
        if channels[chan].is_available():
            updated_channels.add(chan)
# 5) bump_step: every other available channel gets update(EMPTY_SEQ) so
#    EphemeralValues clear and Topic(non-accumulate) resets — with version bumps
# 6) tentative-last-step: if updated_channels ∩ trigger_to_nodes == ∅,
#    call finish() on all channels (AfterFinish channels expose their value)
```
**Flow:** Writes apply in task-path order (deterministic across replicas). Reads are consumed FIRST so a Topic/Barrier resets before new writes land. A node fires when `_triggers()` says: any trigger channel `is_available()` AND `channel_versions[chan] > versions_seen[name][chan]` (null-version compare when never seen; seen==None means availability alone triggers). `should_interrupt` reuses the same version comparison against the special INTERRUPT key's seen-map.

**Invariant:** Unavailable channels can't trigger ("unavailable channels can't trigger tasks, so don't add them"). Null-task writes (no triggers) never bump the step. Versions advance even when values don't change (empty-seq updates), which is what retires ephemeral state deterministically. Interrupt gating requires ANY channel update since the previous interrupt AND a matching task — preventing interrupt loops on frozen state.

**Probe:** `grep -n 'bump_step = ' libs/langgraph/langgraph/pregel/_algo.py` → :259 `any(t.triggers for t in tasks)`; `grep -c 'versions_seen' libs/langgraph/langgraph/pregel/_algo.py` → 3; barrier semantics pinned by `tests/test_pregel.py:2750` waiting-edge comment ("semantics of named barrier (== waiting edges)") + invoke assertion at :2757.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "apply_writes", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-phase write application (consume → update → step-bump → finish) and version-gated triggering — this is what makes "run each node once per state change" correct under concurrency. Adapt the version type (int vs vector clock) freely; keep the null-version comparison for first sight. Omit RESERVED-key filtering only if your host has no reserved write keys.
