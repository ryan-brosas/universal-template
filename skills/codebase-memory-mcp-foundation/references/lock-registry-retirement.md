<!-- capsule-v2 -->
# Lock registry identity retirement — why must a freed registry poison its old pointer?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does `registry_free` owe callers who kept stale handles?

## Refuse active → destroy → retire control identity
**Path/Symbol:** `src/foundation/lock_registry.h:44–49` (contract) + tests/test_lock_registry.c:730–800 (`lock_registry_free_refuses_active_lease`, `lock_registry_free_retires_identity_and_rejects_stale_pointer`).
**Signature:** `cbm_private_file_lock_status_t cbm_lock_registry_free(cbm_lock_registry_t **registry_io);`
**Data Shape:** OK only when no active leases/waiters/pending cleanup; destroys resources, clears *registry_io, and RETIRES the control identity for the process lifetime — copied stale pointers fail with IO instead of aliasing a future registry.

### Decisive source
```c
/* Refuses to free a registry with active leases, waiters, or pending cleanup.
 * OK destroys its resources, clears *registry_io, and retires the control
 * identity for the process lifetime so copied stale pointers cannot alias a
 * future registry; stale operations fail with IO. */
```

**Flow:** free called → active accounting? ⇒ refuse with status (caller retries later) → else destroy tables/leases → bump generation token so any stale pointer's next operation sees a dead identity and returns IO rather than corrupting a NEW registry allocated at the same address.
**Invariant:** Identity retirement is the ABA defense for C handle APIs — freeing without it turns use-after-free into silent cross-registry corruption.
**Probe:** the two named tests plus `lock_registry_terminal_close_error_finishes_pending_accounting`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_lock_registry_free", limit: 5 });
```

## Verdict
Adopt generation-token retirement for all free-able handle types in C; adapt status vocabulary; refusal-on-active is what makes shutdown ordering debuggable.
