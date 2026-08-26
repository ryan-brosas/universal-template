<!-- capsule-v2 -->
# Daemon-owned session manager — how do you keep interactive shells alive across viewer disconnects (no zombies, no mid-command kills) while partitioning them per tenant?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** Who owns a PTY's lifetime when its WebSocket goes away, and how do unknown ids / foreign owners fail?

## Registry + delegation orchestrator
**Path/Symbol:** `packages/server/src/session-manager.ts:SessionManager` (250–884); data model `ManagedSession` (146–207); REST/CLI surface `spawnDetached` (626–636), `kill` (597–612); teardown `handleExit` (829–845) → `tearDown` (847–867); tenant gate `sessionFor` (543–548); composition root `constructor` (263–295).
**Signature:** `class SessionManager { spawn(input, automation?, owner=null): ManagedSession | null; spawnAndAttach(ws, input, automation?, owner=null, windowId=""): ManagedSession | null; attach(ws, id, owner=null, windowId=""): ManagedSession | null; detach(ws): void; kill(id, owner=null): boolean; }`
**Data Shape:** `sessions: Map<string /*session id*/, ManagedSession>`; each entry carries `session` (live PTY wrapper), `clients: Set<ManagedClient>`, `owner` (identity or `null` = operator tier), `pinned`, `graceTimer/parkedAt`, `resizeOwner`, renderers. A session leaves the map ONLY via shell exit, explicit kill, or the lifecycle policy's grace reap (see `session-lifecycle-policy` capsule) — never on client disconnect.

### Decisive source
```ts
// packages/server/src/session-manager.ts:537-548
  // Resolve a live, owned session for an id-based (REST/CLI) operation. Returns
  // null for an unknown/exited id, or when `owner` is set (multi-user mode) and
  // the session belongs to someone else — both surface as not-found to the
  // caller, so a cross-tenant probe can't enumerate or hijack. `owner === null`
  // (the operator/legacy tier) bypasses the check: full access, matching the
  // no-auth behavior exactly.
  private sessionFor(id: string, owner: SessionOwner): ManagedSession | null {
    const managed = this.sessions.get(id);
    if (!managed || managed.session.isExited) return null;
    if (owner !== null && managed.owner !== owner) return null;
    return managed;
  }
```

**Flow:** `spawn` makes room via the lifecycle policy, builds the `ManagedSession` (always-on hibernate renderer pre-seeded from scrollback snapshot), registers listeners, and stores it (474–519) → `spawnAndAttach` composes spawn + hub attach in one step for the WS route (525–535) → clients attach/detach through `SessionClientHub` (550–595) → on shell exit `handleExit` finishes any output burst, pushes `{type:"exit", code}` to every client, closes their sockets, emits the session event, and tears down (829–845) → `tearDown` order matters: cancel grace → dispose capture renderer → clear paste images → stop batch timer/drain poll → dispose git bridge → hub.tearDown (clears clients + resize owner) → delete from registry + pid map → `session.dispose()` in try/catch (847–867). `kill` mirrors handleExit's client-notification loop but works for any tenant-authorized id (597–612).
**Invariant:** a live PTY is never destroyed because its last viewer left — it parks until the grace policy decides; every id-based operation funnels through `sessionFor`, so unknown id, exited shell, and foreign-owner all read as "not found" (no existence leak); `pinned` sessions (REST default, see 184–190 comment) skip the grace entirely.
**Probe:** `tests/session-manager.test.ts::"reaps an idle PTY whose last subscriber detaches and doesn't re-attach in time"` (:41 — detach parks, poll sees size→0 + exited), `"cancels the grace when a subscriber re-attaches within the window"` (:63), `"returns null when attaching to an unknown id"` (:314), `"does not deliver a notification across an owner boundary"` (:785 — owner partition).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "SessionManager spawn attach detach tearDown", limit: 10, fields: ["signature", "name", "file"] });
// trace: SessionClientHub.attach -> SessionManager.sessionFor / SessionLifecyclePolicy.cancelGrace
await mcp.codebase_memory.trace_path({ project: "localterm", function_name: "localterm.packages.server.src.session-client-hub.SessionClientHub.attach", direction: "outbound", depth: 1 });
```

## Verdict
Adopt the registry-that-outlives-disconnects shape (grace window between "last viewer left" and "shell dies"), the not-found-for-everything tenant gate, and the fixed teardown ordering (policy timers cancelled before renderers/transport disposed); adapt the grace duration, identity/owner type, and the pinned-by-default REST policy to your host; omit the automation-run log/redaction plumbing, hibernate/workspace persistence, and keep-awake hooks unless you are building the whole daemon. Direct tests exist and pass upstream (`vite-plus/test` integration suite); coverage caveat: `tests/` is graph-covered in full mode here, but probe lines were read on disk this session.
