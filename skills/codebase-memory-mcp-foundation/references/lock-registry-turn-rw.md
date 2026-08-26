<!-- capsule-v2 -->
# Lock registry turn/rw files — how do you build writer-preference read/write locks from plain file locks?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1b c5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you get fair, cancellable, process-wide RW locks when the OS only gives you named lock objects?

## Turn-file inversion of the requested mode
**Path/Symbol:** `src/foundation/lock_registry.c:lock_registry_attempt_native` (437–510) and name minting (311–312).
**Signature:** `cbm_lock_registry_acquire(registry, resource_key, mode, deadline_ms, cancel_token, cbm_lock_lease_t **lease_out);` — keys bounded to 80-char internal names, hashed into `"cbm-<digest>.turn"` / `"cbm-<digest>.rw"` sidecars.
**Data Shape:** Readers take `.turn` EX then `.rw` SH then RELEASE turn; writers take `.turn` SH then `.rw` EX and HOLD both. Cancel token is a sticky atomic bool; deadlines are absolute `cbm_now_ms()`.

### Decisive source
```c
cbm_private_file_lock_mode_t turn_mode = waiter->mode == CBM_PRIVATE_FILE_LOCK_SH
                                       ? CBM_PRIVATE_FILE_LOCK_EX : CBM_PRIVATE_FILE_LOCK_SH;
status = cbm_private_file_lock_try_acquire(registry->directory, entry->turn_name, turn_mode, &turn);
...
if (waiter->mode == CBM_PRIVATE_FILE_LOCK_SH) { status = cbm_private_file_lock_release(&turn); }
```
```c
/* Rollback and writer release are deliberately rw-before-turn. */
```

**Flow:** try turn in INVERTED mode (readers queue exclusively behind the turn so writers can't starve; writers hold turn SH so many writers share it and block readers) → try rw in the REQUESTED mode → readers drop the turn at once; writers keep it → on any BUSY/IO path abort with rollback (`lock_registry_abort_attempt`) returning a cleanup-only lease that callers MUST release.
**Invariant:** Release order is rw-then-turn for writers; failed acquisition must never strand a half-held pair; stable sidecar names are never unlinked (crash-safe).
**Probe:** `tests/test_lock_registry.c:lock_registry_never_upgrades_shared_lease_in_place`, `lock_registry_cancelled_wait_rolls_back_and_does_not_barge`, `lock_registry_writer_partial_release_retries_rw_then_turn`, `tests/test_private_file_lock.c:private_file_lock_shared_and_exclusive_matrix`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_lock_lease_release", limit: 5 });
```

## Verdict
Adopt the inverted-turn protocol and cleanup-only lease semantics; adapt the native layer (here: owner-only private directory + advisory file locks) to your OS primitives; omit the TSan fault-injection hooks.
