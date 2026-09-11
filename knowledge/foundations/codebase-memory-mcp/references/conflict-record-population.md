<!-- capsule-v2 -->
# Daemon rendezvous conflict record — what exactly should a refused client learn about the build that refused it?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Which fields make a version/build conflict actionable without leaking anything sensitive?

## Both identities + status + 512-byte message, populated even on invalid input
**Path/Symbol:** `src/daemon/service.c:cbm_daemon_hello_compare` (164–189+) + `cbm_daemon_conflict_t` (service.h:48–56).
**Signature:** `cbm_daemon_hello_status_t cbm_daemon_hello_compare(const cbm_daemon_build_identity_t *active, const cbm_daemon_build_identity_t *requested, cbm_daemon_conflict_t *conflict_out);`
**Data Shape:** Always fills active_version/active_build_fingerprint and requested_* BEFORE deciding; status ∈ {INVALID, COMPATIBLE, VERSION_CONFLICT, BUILD_CONFLICT, PROTOCOL_ABI_CONFLICT, STORE_ABI_CONFLICT, FEATURE_ABI_CONFLICT, CACHE_CONFLICT}; message capped at 512.

### Decisive source
```c
if (conflict_out) { memset(conflict_out, 0, sizeof(*conflict_out));
    conflict_out->status = CBM_DAEMON_HELLO_INVALID; }
...
(void)snprintf(conflict_out->active_version, ..., "%s", active->semantic_version);
(void)snprintf(conflict_out->active_build_fingerprint, ..., "%s", active->build_fingerprint);
(void)snprintf(conflict_out->requested_version, ...);
```

**Flow:** compare → whichever check fails sets a SPECIFIC status (version ≠ build ≠ each ABI ≠ cache) → both identity pairs copied so logs on either side name the same two builds → caller renders the message or defaults.
**Invariant:** Populate diagnostics BEFORE validity short-circuits — an INVALID result still records what was asked; specific statuses beat a generic "incompatible".
**Probe:** `tests/test_daemon_version.c:daemon_hello_rejects_each_abi_mismatch`, `daemon_hello_version_conflict_exposes_active_and_requested_builds`, `daemon_hello_fails_closed_without_an_exact_build_fingerprint`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_daemon_conflict_t", limit: 5 });
```

## Verdict
Adopt populate-first conflict records with per-cause statuses for any admission gate; adapt fields; fail-closed on missing fingerprints is the security-relevant half.
