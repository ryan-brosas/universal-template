<!-- capsule-v2 -->

# Related-resources context cache — How do you enrich every emitted event with run lineage without hammering the API?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect` (graph not connected this pass — direct source/test reads; see work record). **Question:** When each event in a long-running worker must carry flow/deployment/queue/pool lineage, how do you keep the per-event read cost bounded?

## Context-first object resolution, parallel cached reads, recency-evicted module cache, role attached at return time

**Path/Symbol:** `src/prefect/events/related.py:related_resources_from_run_context (60-190)`, `_get_and_cache_related_object (193-230)`, `RESOURCE_CACHE`/`MAX_CACHE_SIZE` (30-31), `object_as_related_resource (46-57)`, `tags_as_related_resources (34-43)`.

**Signature:** `async def related_resources_from_run_context(client, exclude: Optional[Set[str]] = None) -> List[RelatedResource]`.

**Data Shape:** cache key `f"{kind}.{obj_id}"`; value `(entry, timestamp)` where entry = `{"kind", "object"}` (+ `"role"` attached only at return); `MAX_CACHE_SIZE = 100`; output order: flow-run, [task-run], flow, deployment, work-queue, work-pool, then sorted tag resources.

### Decisive source
```python
# context-first: the flow-run object comes from contextvars when present;
# only a REMOTE task (no FlowRunContext) triggers an API read:
if flow_run_context:
    related_objects.append({"kind": "flow-run", "role": "flow-run",
                            "object": flow_run_context.flow_run})
else:
    related_objects.append(await _get_and_cache_related_object(
        kind="flow-run", role="flow-run",
        client_method=client.read_flow_run, obj_id=flow_run_id, cache=RESOURCE_CACHE))

# parallel enrichment; absent ids short-circuit to a dummy instead of failing gather:
related_objects += list(await asyncio.gather(
    _get_and_cache_related_object(kind="flow", ..., obj_id=flow_run.flow_id, ...),
    (_get_and_cache_related_object(kind="deployment", ..., obj_id=flow_run.deployment_id, ...)
     if flow_run.deployment_id else dummy_read()),
    ...))

# _get_and_cache_related_object — recency eviction + role NOT cached:
cache_key = f"{kind}.{obj_id}"
if cache_key in cache:
    entry, _ = cache[cache_key]
else:
    obj_ = await client_method(obj_id)
    entry = {"kind": kind, "object": obj_}
cache[cache_key] = (entry, now("UTC"))          # re-touch updates the timestamp
if len(cache) > MAX_CACHE_SIZE:
    oldest_key = sorted([(key, ts) for key, (_, ts) in cache.items()],
                        key=lambda k: k[1])[0][0]
    del cache[oldest_key]
entry["role"] = role                              # event-specific, attached at return
return entry
```

**Flow:** resolve the flow-run from context (or one cached API read for remote workers) → if it is a full FlowRun object, fan out flow/deployment/work-queue/work-pool reads concurrently under `asyncio.gather`, with absent ids replaced by a no-op so one missing field never fails the batch → convert each object via `object_as_related_resource` (duck-typed `as_related_resource(role)` override, else `prefect.{kind}.{id}` + name) → filter by the caller's `exclude` set of resource ids → union all objects' tags and append them as sorted `prefect.tag.*` resources (also exclude-filtered). Every read result is cached process-wide and re-touching an entry refreshes its timestamp, so a long-lived worker re-reads each lineage object at most once until it evicts.

**Invariant:** (1) Context objects must be preferred over reads — the cache exists for the remote-worker case, not to shadow live context. (2) The role is deliberately NOT stored in the cache because the same object can appear under different roles in different events; caching it would cross-contaminate events. (3) Eviction is by oldest TIMESTAMP (recency), and re-touch must update the timestamp or hot entries would age out. (4) A missing optional lineage id (no deployment, no work pool) must short-circuit to a dummy coroutine — raising inside `asyncio.gather` would discard the siblings' results. (5) The cache is unbounded-growth-protected by MAX_CACHE_SIZE precisely because workers are long-lived.

**Probe:** direct tests `tests/events/client/test_events_related_from_context.py`: `:189-200 test_caches_related_objects` (two calls in one flow → `read_flow.assert_called_once()`); `:203-220 test_lru_cache_evicts_oldest` (oldest emoji id gone after MAX_CACHE_SIZE inserts); `:223-235 test_lru_cache_timestamp_updated` (re-touch advances timestamp); `:138-186 test_gets_related_from_task_run_context` (FlowRunContext cleared → flow-run fetched via client, exact 3-resource output); `:49-51 test_gracefully_handles_missing_context` (no context → `[]`).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^related_resources_from_run_context$", "limit": 3}'
```
(expected rank-1: `related_resources_from_run_context Function src/prefect/events/related.py 60-190`; graph was NOT connected in the mining session that authored this capsule — verify live before relying on line numbers.)

## Verdict
Adopt context-first resolution + parallel cached enrichment + recency eviction with role-at-return for any per-event lineage enrichment in long-lived processes. Adapt the kind set and id scheme to your domain; omit Prefect's tag aggregation if your resource model has no tags.
