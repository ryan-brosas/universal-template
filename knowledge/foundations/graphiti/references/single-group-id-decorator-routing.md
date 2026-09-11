<!-- capsule-v2 -->
# Single-group-id decorator routing — the #1659 silent-empty fix

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** when a decorator fans out N-way partitioned calls, why must it ALSO intercept the N=1 case — and how do you clone a driver without corrupting shared state?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/decorators.py:handle_multiple_group_ids` (:29-116) — single-group clone branch (:58-69), multi-group fan-out + typed merge (:72-111), `get_parameter_position` (:119-128); upstream regression pinned by test docstring: issue **#1659**.
**Signature:** `handle_multiple_group_ids(func)` wrapping `async def wrapper(self, *args, **kwargs)`; detects `group_ids` in kwargs OR positionally via `inspect.signature`.
**Data Shape:** host objects expose `self.clients.driver` (provider-checkable) and optional `self.max_coroutines`; merge branches on result type: `SearchResults` → `.merge()`, `list` → flatten, `tuple` → per-component merge (e.g. `build_communities`' `(nodes, edges)`), else raw.

### Decisive source
```python
# decorators.py :30-37 (docstring = the porting lesson)
# Also routes a *single* group_id to the matching FalkorDB graph via a
# call-scoped driver clone. Without this, add_episode re-binds the shared
# driver for writes while search/retrieve with one group_id query the
# driver's default database and silently return empty results (#1659).
if is_falkor and group_ids and len(group_ids) == 1:
    gid = group_ids[0]
    driver = self.clients.driver
    if gid != getattr(driver, '_database', None):
        return await func(
            self, *args,
            **{**kwargs, 'driver': driver.clone(database=gid)},  # injected as kwarg
        )
    return await func(self, *args, **kwargs)
```

**Flow:** resolve `group_ids` from kwargs or positional args → provider gate (`self.clients.driver.provider == FALKORDB`) → ONE group id: if it differs from the driver's current `_database`, inject a cloned driver as the `driver=` kwarg and call through; if equal, plain passthrough → MULTIPLE group ids: per-group concurrent execution (`semaphore_gather`, bounded by `self.max_coroutines`) with positional `group_ids` REMOVED from filtered_args and per-call `[gid]`+clone injected → merge results by declared type.
**Invariant:** (1) N=1 is NOT the passthrough case on partitioned backends — writes rebind the shared driver while reads would hit the default graph and SILENTLY return empty (#1659); (2) the clone is CALL-SCOPED: `host.clients.driver is driver` still holds after the call (test pins identity); (3) already-on-graph short-circuits to zero clones (`gid == driver._database` → no clone, no injected driver kwarg — downstream sees `driver=None`); (4) non-Falkor providers are untouched passthroughs; (5) multi-group merge must strip a POSITIONAL group_ids before re-injection or the callee receives it twice.
**Probe:** `cd $REFERENCE_ROOT/memory/graphiti && grep -c '#1659' graphiti_core/decorators.py` → `1`; `grep -c 'driver.clone(database=gid)' graphiti_core/decorators.py` → `2`; direct tests `tests/test_handle_multiple_group_ids.py::test_falkor_single_group_id_clones_driver_when_database_differs` (:55, asserts `driver.clone_calls == ['acptprobe']`, `host.clients.driver is driver` UNCHANGED, seen db `['acptprobe']`), `::test_falkor_single_group_id_skips_clone_when_already_on_graph` (:71, `clone_calls == []`, seen `[None]`), `::test_non_falkor_single_group_id_is_passthrough` (:96).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "handle_multiple_group_ids clone single group_id SearchResults merge", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "decorator owns partition routing including the N=1 case" for any multi-tenant fan-out API; adapt the provider gate and merge types to your result shapes. The subtle half is preserving SHARED-state identity across clones — a porter who assigns back to `self.driver` turns a correctness fix into a cross-request corruption bug.
