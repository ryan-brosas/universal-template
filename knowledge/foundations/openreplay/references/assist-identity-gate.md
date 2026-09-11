<!-- capsule-v2 -->
# Assist identity gate + JWT authorizer — how does the socket server refuse unknown peers and bind agents to rooms?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600` (ee/ is Enterprise-licensed — patterns only); Codebase Memory `openreplay`. **Question:** What connection-time validation must a co-browsing socket server enforce before joining a session room?

## Handshake query gate, then optional JWT for agents
**Path/Symbol:** `ee/assist/app/assist.js` — `extractPeerId` (:52–66), `processPeerInfo` (:68–78), `check(socket,next)` (:122–154), `IDENTITIES` (:8); room accounting in `ee/assist/app/socket.js` (`onConnect:76–155`, `getRoomData:68–85`, duplicate-tab refusal).
**Signature:** `check(socket: Socket, next: (err?) => void)`; `extractPeerId(peerId): {projectKey, sessionId, tabId}`.
**Data Shape:** handshake query: `identity=agent|session`, `peerId=<projectKey>-<sessionId>[-tabId]`; agents add `auth.token` = `Bearer <jwt(ASSIST_JWT_SECRET)>` carrying matching projectKey/sessionId.

### Decisive source
```js
if (socket.handshake.query.identity === undefined || socket.handshake.query.peerId === undefined) {
    logger.debug(`no identity or peerId, refusing connexion`);
    return socket.disconnect();
}
...
const {projectKey, sessionId} = extractPeerId(...);
if (String(projectKey) !== String(decoded.projectKey) || String(sessionId) !== String(decoded.sessionId)) {
    return next(new Error('Authorization error'));
}
socket.decoded = decoded;
```

**Flow:** connect → identity+peerId present? else disconnect → sessions must carry sessionInfo → peerId parsed to room key; duplicate tabId in room ⇒ SESSION_ALREADY_CONNECTED + disconnect; agents verify JWT claims equal peer-derived ids before join. On any packet `pong` the session's Redis TTL renews (`renewSession`), and a background refresher reconciles per-node local sets into `assist:online_sessions:*` keys with TTL = ping interval.
**Invariant:** Room membership is derived ONLY from validated handshake data (never client-supplied roomId); agent JWT claims must string-match the parsed peer or authorization fails. Sessions are presence-TTL'd, not explicitly deleted.
**Probe:** `grep -c 'refusing connexion' ee/assist/app/socket.js` → `2`; `grep -c 'ASSIST_JWT_SECRET' ee/assist/app/assist.js` → `1`; `grep -c 'assist:online_sessions:' ee/assist/app/cache.js` → `3`. Direct tests: none upstream for ee/ assist (coverage caveat).
**Coverage:** cited ee files clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "authorizer check extractPeerId onConnect IDENTITIES", limit: 10 });
```

## Verdict
Adopt claim-vs-peer binding + presence TTLs. Adapt to your auth stack (the JWT secret/env wiring is host-specific). Omit Redis reconciliation if single-node.
