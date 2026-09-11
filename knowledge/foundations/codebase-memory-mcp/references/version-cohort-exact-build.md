<!-- capsule-v2 -->
# Version cohort — how do you admit only the exact running build across processes and turn over safely?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How can old and new binaries coexist during an upgrade without corrupting shared caches or racing installs?

## Stable rendezvous + exact-build HELLO + lifetime file
**Path/Symbol:** `src/daemon/service.c:cbm_daemon_rendezvous_key` (144–162) + `cbm_daemon_hello_compare` (164+); `src/daemon/version_cohort.c:cbm_version_cohort_reserve_exclusive` (653–659).
**Signature:** `bool cbm_daemon_rendezvous_key(char out[17]);` / `cbm_version_cohort_status_t cbm_version_cohort_acquire(mgr, const cbm_daemon_build_identity_t *identity, deadline_ms, lease_out, conflict_out);`
**Data Shape:** Rendezvous key = FNV-1a-64 of ONE product-domain string → 16 lowercase hex. Build identity = {semantic_version, sha256-of-executable-bytes fingerprint, cache_fingerprint, protocol_abi, store_abi, feature_abi}. Cohort statuses: OK/CONFLICT/BUSY/UNSAFE/IO.

### Decisive source
```c
/* This product-domain string is intentionally the only key input. Account
 * isolation comes from the authenticated IPC runtime, not spoofable text. */
static const unsigned char domain[] = "codebase-memory-mcp:coordination-daemon";
```
```c
/* Admission first takes the maintenance gate SH ... then retains SH on the
 * cohort lifetime file. Active maintenance therefore fails fast with BUSY.
 * Exact identity peers share SH; a different version, build, or ABI returns
 * CONFLICT with conflict_out populated. */
```

**Flow:** every stateful frontend derives the SAME stable key (version/path/fingerprint/cache/ABI deliberately excluded — they must all meet at one endpoint BEFORE HELLO decides) → admission takes maintenance-SH + flips to EX momentarily + retains lifetime-SH → HELLO compares identities; mismatch yields a populated conflict record naming both builds → binary activation takes lifetime EX so no participant is active and none can enter for the whole mutation → coordinated mutation barrier publishes maintenance intent EX first, probes lifetime EX last.
**Invariant:** The endpoint name must never include anything that changes between builds; HELLO must fail CLOSED when the requested fingerprint is missing.
**Probe:** `tests/test_daemon_version.c:daemon_rendezvous_key_is_stable_and_version_independent` + `daemon_hello_accepts_only_the_exact_active_build_identity`; `tests/test_version_cohort.c:version_cohort_shares_exact_build_rejects_conflict_and_turns_over` + `version_cohort_rejects_same_hash_with_different_abi`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_version_cohort_reserve_exclusive", limit: 5 });
```

## Verdict
Adopt "stable rendezvous name, exact-build admission" wholesale — it kills a whole class of mixed-version IPC bugs; adapt the ABI fields to your wire format versions; omit Windows nonce-record plumbing on POSIX targets.
