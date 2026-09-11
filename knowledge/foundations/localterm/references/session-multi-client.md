<!-- capsule-v2 -->
# Multi-client session hub — how do N viewers share one PTY while exactly one client owns its size, one answers terminal queries, and a joiner lands on live output instead of a blank screen?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** What is the per-client state machine that lets many WebSockets fan out from one PTY without fighting over resize, query responses, or the scrollback replay window?

## Attach → pending → promote pipeline
**Path/Symbol:** `packages/server/src/session-client-hub.ts:SessionClientHub.attach` (140–216), `promote` (235–303), `writeInput` (305–319); pending queue types `ManagedClient.pendingQueue` (`session-manager.ts:108–144` — control | output | frame-boundary in ONE queue).
**Signature:** `attach(ws, id, owner=null, windowId=""): ManagedSession | null` (returns session to reattach to, `null` = caller spawns fresh); `async promote(ws, replay: boolean, compress: CompressMode = null, binaryFraming = false): Promise<void>`.
**Data Shape:** `wsToClient: Map<ClientSocket, {client, session}>`; a new client starts `pending: true`, `pendingQueue` seeded with one `output-frame-start` if an atomic frame is open, zero cols/rows, `focused: false`. A `pendingTimer` auto-promotes after `pendingPromoteTimeoutMs` (default 2s) if `{type:"ready"}` never arrives.

### Decisive source
```ts
// packages/server/src/session-client-hub.ts:200-212
    // Auto-promote a client that never sends {type:"ready"} — a back-compat
    // client (an older bundled terminal, or any plain WS reader) would otherwise
    // stay pending and never receive output. The localterm client sends ready
    // within milliseconds of the session frame; the window is sized to clear a
    // mobile/tailscale RTT ...
    client.pendingTimer = setTimeout(
      () => void this.promote(ws, false),
      this.pendingPromoteTimeoutMs,
    );
    client.pendingTimer.unref?.();
```
And the promote-side anti-deadlock (235–303): `replay-end` is sent on EVERY promote path (:271–280), even when `replay === false` — the client opens its suppressed-replay window on the `{session}` frame before its `{ready}` can return, so only the always-sent marker can close it.

**Flow:** attach cancels grace → broadcasts `peer-attached` to existing viewers (skipped for the first client) → registers with the cwd's git coordinator → seeds pending queue from any open atomic frame → promotes first resize owner or recomputes → seeds the joiner with the live `pty-size` WITHOUT resizing the PTY → arms the auto-promote timer → syncs focus reporting. Promote is idempotent (`!client.pending || client.pendingOverflowed` guard :244), clears the timer, resets the Brotli encoder (new attach = stale LZ77 context), announces `compress` mode BEFORE replay so old-server/new-client degrades instead of mis-parsing (:261–265), optionally replays scrollback as one binary frame, then flushes control + buffered output bytes + frame boundaries IN ORDER before flipping `pending = false` and re-pushing the last git summary.
**Invariant:** a promoted client's stream is replay → `replay-end` → buffered messages → live fan-out, with nothing interleaved ahead of the replay; `writeInput` from ANY viewer implicitly promotes it without replay and claims focus/resize ownership (:305–319) — a back-compat client unblocks on its first keystroke.
**Probe:** `tests/session-manager.test.ts::"sends replay-end on an auto-promote so a slow client never deadlocks"` (:350 — never sends ready, still gets replay-end), `::"sends replay-end even when the client asks for no scrollback replay"` (:371), `tests/session-manager.test.ts::"broadcasts peer-attached..."` (:399 — first-attach silence + second-attach single broadcast).

## Resize owner & terminal responder arbitration
**Path/Symbol:** `promoteResizeOwner` (434–440), `latestClientByActivity` (442–457), `recomputeResize` (459–495); responder pair `ensureTerminalResponder`/`assignTerminalResponder` (368–381); input/focus paths `setClientFocus` (327–338), `writeTerminalResponse` (321–325).
**Signature:** `private promoteResizeOwner(managed, client)` bumps `nextActivitySequence += CLIENT_ACTIVITY_SEQUENCE_INCREMENT` and stamps `client.lastActivitySequence` BEFORE the same-owner early-return — recency is recorded even when ownership doesn't change.
**Data Shape:** `resizeOwner: ManagedClient | null` on the session; per-client `cols/rows/pixelWidth/pixelHeight/focused/lastActivitySequence/terminalResponder`.
### Decisive source
```ts
// packages/server/src/session-client-hub.ts:479-483
    // One PTY can only have one size. Following the most recently focused or
    // interactive viewer makes a mobile-to-desktop handoff resize immediately
    // instead of leaving every viewer constrained by the phone. Passive wider
    // clients still receive pty-size so they can mask their dead columns.
```
**Flow:** writeInput/setClientFocus promote the interactive client to resize owner; on blur/detach the owner falls back to the most recent focused client, then any recent client (:410–413); `recomputeResize` applies the OWNER's cols/rows to the PTY, mirrors them into capture/hibernate renderers, tracks `ptySizeWasMultiViewer`, and broadcasts `{pty-size}` only when >1 viewer or when dropping out of multi-viewer (the final mask-clearing frame). The terminal responder is the ONE client whose `writeTerminalResponse` reaches the PTY — query replies follow the most recent writer; detach of the responder reassigns via `ensureTerminalResponder`.
**Invariant:** exactly one size authority at all times (never two clients' resizes interleaving); exactly one query-response receiver (a DSR reply must not be duplicated to every viewer); passive clients learn the effective size via data, never by resizing the PTY themselves.
**Probe:** `tests/session-manager.test.ts::"accepts user input from every viewer but only one generated response"` (:426 — exact PTY write order incl. responder handoff mid-stream), `::"hands PTY size from mobile back to a focused desktop"` (:484), `::"leaves a lone viewer quiet — no pty-size frame on resize"` (:470), `::"lets input reclaim PTY size without a focus frame"` (:542), `::"seeds a wider joiner with the active viewer's current size"` (:572); hub-level focus gating `tests/session-client-hub.test.ts::"injects CSI I on viewer focus only while the app enabled reporting"` (:102), `::"keeps the focused signal while any attached viewer is focused"` (:137 — OR-over-viewers), `::"resets signal state when reporting is disabled, then re-signals on enable"` (:174).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "SessionClientHub promote attach resize owner", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.trace_path({ project: "localterm", function_name: "localterm.packages.server.src.session-client-hub.SessionClientHub.promote", direction: "outbound", depth: 1 });
```

## Verdict
Adopt the pending→promote handshake with always-sent replay-end (kills the slow-client deadlock class), the single resize-owner + single terminal-responder arbitration by activity recency, OR-over-viewers focus-event gating, and peer-attached notification gated to existing viewers; adapt the pending timeout, compress-mode negotiation frames, window/profile identity (`windowId`), and focus/mouse sequence constants to your protocol; omit the Brotli context-takeover encoder specifics, git-metadata coordinator wiring, and workspace-tab persistence unless porting the whole transport. Direct tests exist upstream (integration suite, fake sockets — no real PTY needed for these paths); coverage caveat noted on the manager capsule applies.
