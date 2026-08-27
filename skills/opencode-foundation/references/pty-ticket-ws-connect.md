<!-- capsule-v2 -->
# PTY ticket + WS connect plane — how do you let a browser open a WebSocket to a live terminal without putting credentials in the upgrade URL?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** WebSocket upgrade URLs are visible in history, logs, and proxies, so Basic auth cannot ride the URL — how do you authenticate a terminal-streaming socket from a browser while keeping replay, live output, and close frames in order?

## CSRF-header-gated single-use scoped tickets
**Path/Symbol:** `packages/opencode/src/server/shared/pty-ticket.ts` (whole, 15L) + `packages/core/src/pty/ticket.ts` (`make` :38-52, `noLookup` :35) + `packages/opencode/src/server/routes/instance/httpapi/handlers/pty.ts` (`connectToken` :144-149, `ptyConnectHandlers` connect :186-268) + `groups/pty.ts` (`PtyConnectApi` :139-172) + `middleware/authorization.ts:143`.
**Signature:** `issue({ptyID, directory?, workspaceID?}) → Effect<{ticket: string, expires_in: number}>`; `consume(same scope & {ticket}) → Effect<boolean>`; constants `PTY_CONNECT_TICKET_QUERY="ticket"`, `PTY_CONNECT_TOKEN_HEADER="x-opencode-ticket"`, value `"1"`.
**Data Shape:** ticket = `crypto.randomUUID()` stored in an Effect Cache (TTL 60s, capacity 10,000) keyed by ticket → scope `{ptyID, directory, workspaceID}`; the cache lookup function DIES if ever called (`noLookup` :35) — entries are only written via set and removed via `invalidateWhen`.

### Decisive source
```ts
// core/pty/ticket.ts:48-50 — consume is an ATOMIC scoped single-use delete:
consume: Effect.fn("PtyTicket.consume")(function* (input) {
  return yield* Cache.invalidateWhen(cache, input.ticket, (stored) => matches(stored, input))
})
// handlers/pty.ts:144-149 — token minting needs BOTH a CSRF-style header AND a valid origin:
if (request.headers[PTY_CONNECT_TOKEN_HEADER] !== PTY_CONNECT_TOKEN_HEADER_VALUE || !validOrigin(request, cors))
  return yield* new ApiError.PtyForbiddenError({ message: "Invalid PTY connect token request" })
yield* get(ctx)
return yield* tickets.issue({ ptyID: ctx.params.ptyID, ...(yield* ticketScope) })
// handlers/pty.ts:187-200 — connect ordering: existence FIRST, then decode, then ticket:
if (!exists) return HttpServerResponse.empty({ status: 404 })
const query = Schema.decodeUnknownOption(CursorQuery)(yield* HttpServerRequest.ParsedSearchParams)
if (Option.isNone(query)) return HttpServerResponse.empty({ status: 400 })
const ticket = new URL(ctx.request.url, "http://localhost").searchParams.get(PTY_CONNECT_TICKET_QUERY)
if (ticket) {
  const valid = validOrigin(ctx.request, cors)
    ? yield* tickets.consume({ ticket, ptyID: ctx.params.ptyID, ...(yield* ticketScope) })
    : false
  if (!valid) return HttpServerResponse.empty({ status: 403 })
}
```

**Flow:** client (authenticated via normal API auth) POSTs `/pty/:id/connect-token` with header `x-opencode-ticket: 1` and a CORS-valid origin ⇒ gets `{ticket, expires_in:60}`; the WS upgrade to `/pty/:id/connect?ticket=...&cursor=-1` uses `PtyConnectAuthorization`, which skips Basic auth exactly when the URL matches `/pty/:id/connect` AND carries a ticket param (authorization.ts :143). Handler order is pinned by tests: running-session existence check first (empty 404 before ANY query decoding), cursor query decode (400), ticket consume (403 when invalid OR origin mismatch; absent ticket falls through to normal auth), cursor validated as safe integer ≥ -1. After upgrade: register a close-effect in the WebSocketTracker (reject if server is closing), build ONE unbounded outbox queue drained by a single writer so replay chunks, live data, and the close frame keep their order (:225-256); attach errors (NotFound/Exited) become close code 4404 "session not found"; replay chunks + `metaFrame(cursor)` are queued BEFORE `attachment.activate()` so late output can never precede replay; reader and writer race, whichever finishes ends the connection, `attachment.detach()` runs in ensuring. Legacy `/pty/*` surface HIDES exited sessions (list filters `status==="running"`, get→404 for exited, :38-41 comment + :66 + :95-101) preserving pre-retention client behavior, while canonical `/api/pty/*` retains them with exitCode. Create merges plugin `shell.env` hook output OVER caller env (`{...payload.env, ...shell.env}`, :78); core forces PTY values (TERM=xterm-256color) after the plugin env.
**Invariant:** A ticket is single-use (atomic invalidateWhen), TTL-bounded (60s), and scope-bound — it cannot open a PTY in another directory/workspace even within TTL. The upgrade URL never carries credentials. Replay must fully precede live output on the wire. Exited-session visibility differs BY DESIGN between legacy and canonical surfaces.
**Probe:** `packages/opencode/test/server/httpapi-pty.test.ts:183-197` ("returns 404 for missing PTY websocket before upgrade" and "before decoding cursor query" pin the 404-before-decode ordering); `:226-253` (connect-token without header → 403 `PtyForbiddenError`, with header but missing session → 404); `test/server/httpapi-v2-pty.test.ts:103-128` ("rejects connect tokens without the CSRF header" → 403, `ticket=not-a-ticket` → 403); `:66-93` (canonical surface retains exited session with `exitCode: 4`); source pin:
```bash
grep -n 'invalidateWhen' packages/core/src/pty/ticket.ts
grep -n 'hasPtyConnectTicketURL' packages/opencode/src/server/routes/instance/httpapi/middleware/authorization.ts
```
expect 3 + 2 hits (comment + noLookup die-message + consume; import + :143 skip).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "PtyTicket issue consume invalidateWhen connect-token x-opencode-ticket", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase pattern (authenticated mint endpoint gated by a trivial CSRF header + origin check, then single-use TTL-scoped ticket in the upgrade URL) for any browser-initiated WebSocket that cannot carry credentials; adopt the one-outbox-single-writer ordering discipline and replay-before-activate for any attach-with-replay stream; adopt the die-on-lookup cache as a misuse tripwire. Adapt TTL/capacity and the scope fields to your tenancy model; omit opencode's legacy-surface exited-hiding unless you have pre-retention clients. Direct tests read whole (httpapi-pty.test.ts 299L, httpapi-v2-pty.test.ts 250L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
