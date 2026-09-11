<!-- capsule-v2 -->
# Daemon IPC transport — what makes a local Unix-socket daemon safe enough to trust with account-wide coordination?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What endpoint, publication, and probe design prevents socket squatting and stale-name confusion?

## Owner-only runtime dir + anchor/temp-link publication + active-probe
**Path/Symbol:** `src/daemon/ipc.h` (contract 1–131) + `cbm_daemon_ipc_endpoint_probe` semantics; Windows nonce-record twin in ipc.c:150–212.
**Signature:** `cbm_daemon_ipc_endpoint_t *cbm_daemon_ipc_endpoint_new(const char *instance_key, const char *runtime_parent);` / `int cbm_daemon_ipc_endpoint_probe(endpoint, timeout_ms);`
**Data Shape:** POSIX addresses deterministic from a validated 16-lowercase-hex instance key (`cbm-<key>.sock`); listener publication binds a PRIVATE generation anchor, durably records pending identity via recoverable deterministic temp link, then HARD-LINKS the anchor into the stable socket name. A "secure but refused" connect also fails closed as ACTIVE (BSD behavior). Handles non-inheritable.

### Decisive source
```c
/* POSIX listener publication binds a private generation anchor, durably
 * records the pending anchor identity through a recoverable deterministic
 * temp link, hard-links the anchor into the stable socket name without ... */
/* ... secure but refused Unix socket also fails closed as active because BSD
 * may [report ECONNREFUSED for an alive-but-busy peer] */
/* Remove only a provably current-generation stale Unix socket identity. */
```

**Flow:** derive endpoint under an owner-only directory (callers duplicate the validated handle; never reopen paths) → daemon publishes via anchor→hard-link so a crash between steps leaves recoverable state → clients connect to the stable name → probe classifies absent vs active (refused ⇒ active, fail closed) → stale identity removal requires proving current-generation ownership.
**Invariant:** Account isolation comes from the OS (directory ACL / current-user named pipe), never from caller-supplied text; stable names are never blindly unlinked.
**Probe:** `tests/test_daemon_ipc.c` (118 tests incl. `daemon_ipc_windows_rendezvous_record_is_exact_and_canonical`, generation-address binding), plus host reconcile twins in tests/test_daemon_runtime.c.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_daemon_ipc_endpoint_new", limit: 5 });
```

## Verdict
Adopt OS-scoped endpoints + atomic-ish publication + fail-closed probes for any account-local daemon; adapt the named-pipe twin on Windows; keep stale-cleanup behind generation proofs.
