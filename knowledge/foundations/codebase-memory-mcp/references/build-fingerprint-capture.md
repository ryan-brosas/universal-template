<!-- capsule-v2 -->
# Daemon build fingerprint — why hash the executable BYTES instead of trusting a version string?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How is the 64-hex build identity computed, when, and what does "exact build" actually pin?

## SHA-256 over exact executable bytes, captured once at startup
**Path/Symbol:** `src/daemon/service.c:digest_to_hex` (134–142) + `cbm_daemon_build_fingerprint` (header 60+) + supervisor capture in src/mcp/index_supervisor.c:117–145.
**Signature:** `bool cbm_daemon_build_fingerprint(char out[CBM_DAEMON_BUILD_FINGERPRINT_SIZE]);`
**Data Shape:** 32-byte SHA-256 of the running image → 64 lowercase hex. Captured ONCE during process startup (before any worker launch); repeated calls return the original so an installer swapping the file mid-session cannot cause re-hashing divergence.

### Decisive source
```c
/* Capture the exact executable-image fingerprint once, during process startup
 * before any worker can be launched. Repeated calls return the original capture
 * and never re-hash a pathname that an installer may since have replaced. */
static const char hex[] = "0123456789abcdef";
```

**Flow:** process entry → read own image bytes → sha256 → hex-encode → cache → every HELLO/cohort admission presents this string; peers compare byte-exactly — same version number with different bytes ⇒ BUILD_CONFLICT.
**Invariant:** Cache-at-startup is semantic (TOCTOU defense), not optimization; version strings are marketing, fingerprints are identity.
**Probe:** `tests/test_daemon_version.c:daemon_build_fingerprint_hashes_exact_executable_bytes`; supervisor twin tests/test_index_supervisor.c argv grammar requires the fingerprint argument.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "build_fingerprint", limit: 5 });
```

## Verdict
Adopt content-hash identity for self-coordinating binaries; adapt hashing to your platform's image access; capture-once ordering is the invariant that matters.
