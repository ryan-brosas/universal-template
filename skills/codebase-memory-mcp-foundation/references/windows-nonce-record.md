<!-- capsule-v2 -->
# Daemon IPC Windows nonce — how do you secure named-pipe endpoints where the filesystem can't hold identity?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What replaces socket-file ownership proofs on Windows?

## Nonce record with exact canonical form
**Path/Symbol:** `src/daemon/ipc.c:150–212` (`daemon_ipc_windows_rendezvous_record_is_exact_and_canonical`) + ipc.h contract.
**Signature:** nonce-record write/read helpers around `\\.\pipe\<name>` creation.
**Data Shape:** A rendezvous record (nonce + generation identity) is durably stored and re-read EXACTLY byte-for-byte; canonical spelling pinned so different writers produce identical records — any deviation ⇒ squatting suspicion.

### Decisive source
```c
TEST(daemon_ipc_windows_rendezvous_record_is_exact_and_canonical) { ... }
```

**Flow:** server creates pipe under current-user namespace → writes canonical nonce record → clients read+verify before trusting HELLO → mismatched/stale records fail closed.
**Invariant:** Where Unix gets owner-only directory isolation for free, Windows needs an explicit proof artifact; its format must be frozen or cross-build coordination breaks.
**Probe:** `tests/test_daemon_ipc.c:daemon_ipc_windows_rendezvous_record_is_exact_and_canonical` plus generation-address tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "rendezvous_record", limit: 5 });
```

## Verdict
Adopt explicit nonce/identity artifacts on platforms without POSIX socket semantics; adapt record format; pin canonical serialization with a dedicated test.
