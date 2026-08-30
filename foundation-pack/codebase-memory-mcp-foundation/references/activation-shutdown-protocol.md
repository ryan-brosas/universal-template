<!-- capsule-v2 -->
# Daemon activation shutdown — how do you ask a CONFLICTING build to shut down when normal HELLO refuses you?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What first-frame protocol remains parseable across versions that would otherwise fail the identity check?

## u32 action + unchanged 133-byte identity, 24-byte reply
**Path/Symbol:** `src/daemon/runtime.h:47–58`.
**Signature:** `CBM_DAEMON_ACTIVATION_SHUTDOWN_REQUEST_SIZE 137U` (u32 action @0 + rendezvous identity @4); response 24 bytes: u32 rendevous ABI @0, u32 accepted @4, u64 active-client snapshot @8, u64 drained-connection snapshot @16 (requester excludes itself).
**Data Shape:** Deliberately carries ONLY the frozen rendezvous identity — no new fields that an older build couldn't parse. Accepted ⇒ daemon begins orderly quiesce; snapshots let the installer report liveness.

### Decisive source
```c
/* Cross-version activation shutdown is a separate first-frame protocol which
 * remains parseable when normal HELLO would report a version/build conflict.
 * Request: u32 action @0 followed by the unchanged 133-byte rendezvous
 * identity @4. Response: ... u64 active client snapshot @8, u64 drained-
 * connection snapshot @16 (the activation requester excludes itself). */
```

**Flow:** new binary wants to install → cohort shows conflicting build → send action+identity on the SAME stable endpoint → old build parses it because the layout is generation-zero frozen → old build drains and replies with snapshots → new binary proceeds with exclusive reservation (see version-cohort capsule).
**Invariant:** The escape hatch must share the frozen envelope exactly; adding convenience fields here would break the very upgrades it exists to enable.
**Probe:** size constants pinned by tests/test_daemon_ipc.c; end-to-end turn-over in tests/test_version_cohort.c:136 (`..._rejects_conflict_and_turns_over`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "activation_shutdown", limit: 5 });
```

## Verdict
Adopt minimal cross-version escape protocols sharing the frozen header for self-upgrading systems; adapt action codes; snapshot exclusion semantics prevent miscounting yourself.
