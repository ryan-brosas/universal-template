<!-- capsule-v2 -->
# process-owned-host-lifecycle — how does the client keep exactly one host process alive across sessions?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How is the sandbox host spawned, shared, re-connected, and drained — and what happens to in-flight opens when shutdown races connect?

## Lazy single-connection provider
**Path/Symbol:** `codex-rs/code-mode/src/remote_session.rs` : `OwnedCodeModeHost::connection` (:212-236), `SessionState` FSM (:256-265).
**Data Shape:** endpoint = Process(path) or WebSocket{url, client_factory}; ONE live connection per provider guarded by a 1-permit Semaphore (connect coalescing); session state = New → Opening{remote, result_rx} → Open(binding) → Closing → Closed; generation counter disambiguates stale opens.

### Decisive source
```rust
let _connect_permit = self.connect_permit.acquire().await...?;
if let Some(connection) = self.live_connection() { return Ok(connection); }  // re-check UNDER permit
let new_connection = match &self.endpoint {
    HostEndpoint::Process(host_program) => Connection::spawn(host_program).await?,
    ...
```

**Flow:** availability() checks the executable exists WITHOUT spawning (fail-fast for tool-surface decisions) → first create_session opens the connection AND the remote session before returning → dead connection on an Open session: retain old cleanup, reset to New, loop. Shutdown driver handles all five states including "Opening" (wait for the open to finish, then close) and double-entry (loud error).
**Invariant:** The spawn uses `process_group(0)` + `kill_on_drop(true)` + scrubbed env (`scrub_non_inheritable_env_vars`) so the host cannot outlive the client or leak secrets via env. Drop of a ProcessOwnedCodeModeSession requests shutdown only when inside a tokio runtime (`Handle::try_current().is_ok()`). Retired cleanups are retained until complete so a replaced connection's session-close is still awaited at shutdown.
**Probe:** `code-mode/src/remote_session_tests.rs` (390 lines) at pin covers reconnect + shutdown races.

## Spawn handshake hygiene
**Path/Symbol:** `code-mode/src/remote_session/connection.rs` : `Connection::spawn` (:215-262), `establish` (:283+).
**Data Shape:** 10s handshake timeout; stderr piped and logged line-by-line (never mixed into the framed protocol); optional capabilities advertised by CLIENT (dual-websocket only when bulk options present); unexpected bulk token from host = hard error.
**Flow:** hello → HostHello V1 → capability echo check → bulk pairing token iff dual capability negotiated.
**Invariant:** Client sends EMPTY required-capabilities (all optional) so older hosts interoperate; hosts must reject unknown REQUIRED capabilities — that asymmetry is the versioning mechanism.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "OwnedCodeModeHost SessionState Opening kill_on_drop", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy single-host ownership with permit-coalesced connects, generation-tagged opens, and state-complete shutdown drivers. Adapt transport spawn details. Omit install-context path resolution.
