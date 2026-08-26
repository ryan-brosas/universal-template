<!-- capsule-v2 -->
# Store idle release — how do you keep a long-running MCP server from holding a store (and its locks) forever?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What TTL discipline releases cached stores, and what special case frees a pristine in-memory one?

## Idle-timeout close + pristine-memory fast release
**Path/Symbol:** `src/mcp/mcp.c` — idle release (1798–1816) + `cbm_mcp_server_release_pristine_memory_store` (1822–1831).
**Signature:** `static void release_idle_store(cbm_mcp_server_t *srv, long timeout_s);` / `bool cbm_mcp_server_release_pristine_memory_store(cbm_mcp_server_t *srv);`
**Data Shape:** Idle release fires when `now - store_last_used >= timeout_s` and the server OWNS the store; closes it, NULLs handle+project, resets last_used. Pristine release requires: owns_store ∧ store ∧ !current_project ∧ last_used==0 ∧ db_path==":memory:"-class (NULL path).

### Decisive source
```c
if ((now - srv->store_last_used) < timeout_s) return;
if (srv->owns_store) cbm_store_close(srv->store);
srv->store = NULL; free(srv->current_project); srv->current_project = NULL;
srv->store_last_used = 0;
...
bool ok = !srv->current_project && srv->store_last_used != 0 ... /* pristine guard */
```

**Flow:** every resolve stamps `store_last_used` → periodic/idle check closes owned stores past the TTL so file locks and WAL readers don't linger for days-long sessions → tests can additionally drop an unused in-memory store instantly via the pristine predicate.
**Invariant:** Only OWNED stores are closed (borrowed handles belong elsewhere); the last-used stamp must update on EVERY use or you close hot stores.
**Probe:** `tests/test_mcp.c` server-lifecycle coverage plus `has_cached_store` consumers; daemon-side twin in application job teardown.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "release_pristine_memory_store", limit: 5 });
```

## Verdict
Adopt ownership-checked TTL release with an explicit test-only pristine valve; adapt timeout to session norms; nothing else exotic.
