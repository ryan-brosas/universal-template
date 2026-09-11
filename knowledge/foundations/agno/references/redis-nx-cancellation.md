<!-- capsule-v2 -->
# Redis NX cancellation — How is intent preservation guaranteed atomically across processes?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What is the distributed twin of setdefault-intent, and why a pipeline for cancel?

## SET NX on register; pipeline EXISTS+SET on cancel
**Path/Symbol:** `libs/agno/agno/run/cancellation_management/redis_cancellation_manager.py:register_run/_cancel_via_pipeline` (:88-137).
**Signature:** `register_run(run_id: str) -> None`; `_cancel_via_pipeline(client, key: str) -> bool`; key = namespaced via `_get_key(run_id)`, TTL = `self.ttl_seconds`.
**Data Shape:** value is the string "0"/"1" (not flags); sync and async clients supported (`_ensure_sync_client`/`_ensure_async_client` raising RuntimeError when the wrong flavor is configured); works with standalone Redis and RedisCluster.

### Decisive source
```python
def register_run(self, run_id: str) -> None:
    """Uses NX flag to preserve any existing cancellation intent."""
    client = self._ensure_sync_client()
    key = self._get_key(run_id)
    # NX: only set if key does not exist, preserving cancel-before-start intent
    client.set(key, "0", ex=self.ttl_seconds, nx=True)

def _cancel_via_pipeline(self, client, key: str) -> bool:
    pipe = client.pipeline()
    pipe.exists(key)
    if self.ttl_seconds and self.ttl_seconds > 0:
        pipe.set(key, "1", ex=self.ttl_seconds)
    else:
        pipe.set(key, "1")
    results = pipe.execute()
    return bool(results[0])
```

**Flow:** register writes "0" only if absent (NX ≙ in-memory setdefault); cancel pipelines EXISTS (returns was_registered) with SET "1" (+EXPIRE when TTL configured); is_cancelled reads the flag; cleanup DELs the key.
**Invariant:** NX on register is the whole point — an unconditional SET would clobber another process's cancel. The cancel pipeline exists to return was_registered atomically with the write; two separate round-trips would let the key expire between them and misreport. TTL bounds stale cancelled keys when runs die without cleanup.
**Probe:** `grep -c 'nx=True' libs/agno/agno/run/cancellation_management/redis_cancellation_manager.py` → **2** (sync + async register twins); direct behavior test `libs/agno/tests/integration/agent/test_agent_run_cancellation.py::test_cancel_non_existent_agent_run` (cancel of unregistered run stores intent rather than erroring).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "redis cancellation manager ttl pipeline", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the NX/pipeline pair as the canonical distributed intent latch; adapt key namespace + TTL to your deployment; omit cluster-specific client plumbing if single-node.
