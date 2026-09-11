<!-- capsule-v2 -->
# Daemon conflict log — where do you record "another build tried to run" so upgrades are debuggable?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What durability, privacy, and rotation guarantees does the cross-build conflict record need?

## Durable private rotating sidecar with stable-name serialization
**Path/Symbol:** `src/daemon/service.c` (conflict log) + tests/test_daemon_version.c:318–377 (`daemon_conflict_log_is_durable_private_and_rotates`, `daemon_conflict_log_rotation_serializes_on_stable_sidecar`).
**Signature:** invoked from `cbm_daemon_hello_compare` failure paths with a populated `cbm_daemon_conflict_t`.
**Data Shape:** Record carries both active and requested identity {version, build_fingerprint(64-hex), cache_fingerprint} + status + message; file is owner-private, fsync-durable, rotated under a STABLE sidecar lock name so concurrent writers serialize.

### Decisive source
```c
TEST(daemon_conflict_log_is_durable_private_and_rotates) { ... }
TEST(daemon_conflict_log_rotation_serializes_on_stable_sidecar) { ... }
```

**Flow:** HELLO mismatch → populate conflict (active/requested versions+fingerprints, status enum) → append to conflict log under the rotation lock → fsync → trim/rotate by count → admission decision proceeds independently of logging success.
**Invariant:** Logging must never block or fail admission (diagnostics, not control flow); rotation needs its own lock because two conflicting builds write concurrently — that's the whole scenario.
**Probe:** the two named tests; conflict population asserted in `daemon_hello_version_conflict_exposes_active_and_requested_builds`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "conflict", limit: 5 });
```

## Verdict
Adopt best-effort durable conflict journals for multi-version coordination; adapt rotation policy; the serialize-on-stable-sidecar detail is what makes concurrent conflicting writers safe.
