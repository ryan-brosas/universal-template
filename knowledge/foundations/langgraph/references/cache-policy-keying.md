<!-- capsule-v2 -->
# Cache-policy keying — How are task writes cached and reused across runs without re-execution?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** A node/task with a `CachePolicy` should not re-run when its inputs repeat — how is the key built, where are writes stored, and at what point does a cache hit short-circuit execution?

## Key = (namespace, xxh3(user key_func output)); value = the task's WRITES; hit = pre-filled writes
**Path/Symbol:** key build: `libs/langgraph/langgraph/pregel/_algo.py` — PULL node :668-687, functional call :859-870, Send push :1019-1032, error handler :1167-1180. Hit: `libs/langgraph/langgraph/pregel/_loop.py:PregelLoop.match_cached_writes` (:1549-1562) + driver loop `libs/langgraph/langgraph/pregel/main.py` :2964-2968. Miss-store: `_loop.py:put_writes` (:1609-1625 sync, :1864-1883 async). Key type: `libs/langgraph/langgraph/types.py:CacheKey` (:655-663).
**Signature:** `CacheKey(ns: tuple[str, ...], key: str, ttl: int | None)`; `CachePolicy(key_func: Callable[..., str | bytes], ttl: int | None)`; `BaseCache.get(keys: tuple[(ns, key), ...]) -> dict[(ns, key), list[(channel, value)]]`, `set({(ns, key): (writes, ttl)})`.
**Data Shape:** ns is always `(CACHE_NS_WRITES, identifier(proc) or "__dynamic__", node_name)` — per-function namespace plus the executing node name; key is `xxh3_128_hexdigest(key_func(args))` where args differ by path (node input / call args / Send packet.arg / failed task input).

### Decisive source
```python
# _loop.py — hit path: only tasks that have a key AND no writes yet
    def match_cached_writes(self) -> Sequence[PregelExecutableTask]:
        if self.cache is None:
            return ()
        matched: list[PregelExecutableTask] = []
        if cached := {
            (t.cache_key.ns, t.cache_key.key): t
            for t in self.tasks.values()
            if t.cache_key and not t.writes
        }:
            for key, values in self.cache.get(tuple(cached)).items():
                task = cached[key]
                task.writes.extend(values)
                matched.append(task)
        return matched

# main.py driver loop — cached tasks never reach the runner
                while loop.tick():
                    for task in loop.match_cached_writes():
                        loop.output_writes(task.id, task.writes, cached=True)
                    for _ in runner.tick(
                        [t for t in loop.tasks.values() if not t.writes],
                        ...
```

**Flow:** Every task-prep path attaches a `cache_key` when a policy exists (per-task policy wins over graph default). After each `tick()` prepares tasks, `match_cached_writes()` batch-gets all keyed write-less tasks and extends their writes from the cache; those hits stream immediately with `cached=True`, and the runner executes only tasks whose writes are still empty. On completion, `put_writes` asynchronously stores `(task.writes, ttl)` under the same key. The async twin refuses to store when `writes[0][0] in (INTERRUPT, ERROR)` ("only cache successful tasks", `_loop.py:1872-1874`); the sync twin has no such guard at this pin (observed asymmetry — treat as caveat, not contract). Because the stored value is the full write list, a cache hit reproduces exactly what the original run wrote to channels — including multi-channel outputs — without any node code running.
**Invariant:** Caching is keyed on user-declared input identity (`key_func`), namespaced per function+node, and stores effects (writes) rather than return values — so a hit is indistinguishable from a real run downstream. Only write-less tasks are cache candidates, which keeps checkpoint-pending-write replay (resume) authoritative over the cache.
**Probe:** `python -m pytest "tests/test_pregel.py::test_no_redundant_put_writes_for_cached_task" -q -k memory` — passes (cached @task on resume produces no redundant put_writes). Byte-exact: `grep -c 'if t.cache_key and not t.writes' libs/langgraph/langgraph/pregel/_loop.py` → 2 (sync + async twins); `grep -c '# only cache successful tasks' libs/langgraph/langgraph/pregel/_loop.py` → 1 (async only); `grep -c 'CACHE_NS_WRITES' libs/langgraph/langgraph/pregel/_algo.py` → 5 (import + four prep paths).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "CACHE_NS_WRITES CacheKey cache policy", limit: 8 });
```

## Verdict
Adopt the three-part contract: (1) keys derived from a user-supplied key function over inputs, hashed and namespaced per callable; (2) values are the durable write list, not a return value; (3) matching happens once per superstep before execution, and hits simply pre-fill writes so the normal apply/stream path handles them. Adapt TTL handling to your store. Omit the sync/async guard asymmetry — port the async rule (never cache INTERRUPT/ERROR writes) to BOTH paths.
