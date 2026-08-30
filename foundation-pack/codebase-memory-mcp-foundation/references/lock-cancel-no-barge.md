<!-- capsule-v2 -->
# Lock registry cancellation — how do you wake a parked lock waiter without letting it barge past queued peers?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What semantics must sticky cancel tokens have so rollback is clean and fairness holds?

## Sticky token + wake + rollback-to-BUSY (no barging)
**Path/Symbol:** `src/foundation/lock_registry.h:24–29` (token contract) + tests/test_lock_registry.c:149–240 (`lock_registry_cancelled_wait_rolls_back_and_does_not_barge`, `lock_registry_failed_rollback_returns_cleanup_only_lease`).
**Signature:** `cbm_private_file_lock_status_t cbm_lock_registry_request_cancel(cbm_lock_registry_t *registry, cbm_lock_cancel_token_t *token);` — `typedef atomic_bool cbm_lock_cancel_token_t;`
**Data Shape:** Cancel "stores true with release ordering and wakes registry waiters"; the TOKEN outlives every acquisition observing it; tokens are never reset by the registry. Clean cancel/deadline expiry returns BUSY with NULL lease.

### Decisive source
```c
/* Sticky cancellation: stores true with release ordering and wakes registry
 * waiters. The token must outlive every acquisition that observes it. */
...
TEST(lock_registry_cancelled_wait_rolls_back_and_does_not_barge) { ... }
```

**Flow:** waiter parks on turn/rw contention → owner/caller sets token (release store) + registry wakes waiters → cancelled waiter rolls back any partial native locks → returns BUSY/NULL WITHOUT re-attempting acquisition ahead of already-queued peers.
**Invariant:** Cancellation must be atomic with wake-up (release ordering) and must not confer priority — a barging cancelled waiter starves everyone behind it.
**Probe:** the two named tests plus `lock_registry_abort_lock_failure_returns_waiter_cleanup_lease`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_lock_registry_request_cancel", limit: 5 });
```

## Verdict
Adopt sticky tokens + no-barge rollback for cancellable locks; adapt to condvar/futex primitives; the cleanup-only-lease pattern pairs with it.
