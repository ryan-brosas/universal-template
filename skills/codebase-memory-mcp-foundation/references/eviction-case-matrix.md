<!-- capsule-v2 -->
# Idle eviction tests — what's the four-case matrix for store cache eviction?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Which eviction cases must be pinned so TTL logic never regresses?

## Evict / keep / protect-initial / touch-resets matrix
**Path/Symbol:** `src/mcp/mcp.c:cbm_mcp_server_evict_idle` + tests/test_mcp.c:7647–7726 (`store_idle_eviction`, `store_idle_no_eviction_within_timeout`, `store_idle_evict_protects_initial_store`, `store_idle_evict_access_resets_timer`).
**Signature:** `void cbm_mcp_server_evict_idle(cbm_mcp_server_t *srv, long timeout_s);`
**Data Shape:** (1) timeout 0 after a tool call ⇒ evicted; (2) huge timeout ⇒ kept; (3) initial in-memory store (never used via named project, last_used==0) ⇒ NEVER evicted; (4) access resets the timer.

### Decisive source
```c
/* Evict with 0s timeout → should evict immediately */
cbm_mcp_server_evict_idle(srv, 0);
ASSERT_FALSE(cbm_mcp_server_has_cached_store(srv));
...
/* should NOT evict the initial in-memory store (store_last_used == 0). */
cbm_mcp_server_evict_idle(srv, 0);
ASSERT_TRUE(cbm_mcp_server_has_cached_store(srv));
```

**Flow:** tool call stamps last_used → periodic evict checks age vs timeout → close owned stores only → NULL-server call must be a no-op.
**Invariant:** The pristine-store protection prevents the bootstrap store from being yanked before any request; timer-reset-on-use is what makes "idle" mean idle.
**Probe:** the four named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "evict_idle", limit: 5 });
```

## Verdict
Adopt explicit case-matrix tests for any TTL cache; adapt timeouts; always protect the pre-use initial state explicitly.
