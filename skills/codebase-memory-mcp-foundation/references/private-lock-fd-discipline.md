<!-- capsule-v2 -->
# Private file lock fd discipline — what does close(2) failure mean for a lock, and how do you avoid fd-reuse corruption?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How should lock release handle EINTR-class close errors without double-unlocking or leaking the fd?

## POSIX close consumes ownership even on error; terminal IO clears the handle
**Path/Symbol:** `src/foundation/private_file_lock.h:33–40` (contract) + tests/test_private_file_lock.c:395–483 (`unlock_failure_retains_retryable_lock`, `close_failure_retries_without_duplicate_unlock`, `consumed_close_error_never_retries_recycled_fd`).
**Signature:** `cbm_private_file_lock_status_t cbm_private_file_lock_release(cbm_private_file_lock_t **lock_io);`
**Data Shape:** OK terminally closes and clears *lock_io. IO retains a non-NULL object ONLY while native ownership is safely retryable; a consumed close (POSIX semantics) clears it to prevent fd-reuse races where a recycled descriptor gets unlocked by mistake.

### Decisive source
```c
/* OK terminally closes the native handle and clears *lock_io. IO retains a
 * non-NULL object only while native ownership is safely retryable. POSIX
 * close(2) consumes descriptor ownership once invoked even if it reports an
 * error, so that terminal IO case clears *lock_io to prevent fd-reuse races. */
```

**Flow:** release → unlock region → close fd → on close error, because POSIX already consumed the fd, clear the handle (retrying would unlock a recycled fd) → unlock errors BEFORE close retain the object for one retry.
**Invariant:** Distinguish "operation failed but state intact" from "operation consumed the resource"; conflating them causes double-release on recycled descriptors.
**Probe:** the three named tests plus `private_file_lock_shared_and_exclusive_matrix`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_private_file_lock_release", limit: 5 });
```

## Verdict
Adopt consume-on-invoke clearing for any close-like teardown; adapt to Windows CloseHandle semantics; the shared/exclusive try-acquire matrix is reusable as-is.
