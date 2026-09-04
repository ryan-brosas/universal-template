<!-- capsule-v2 -->
# ws-dead-version-protocol — How does a server tell connected clients it is defunct without killing their sockets, and how is the version string weaponized for draining?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** What mechanism lets an old server make new connections read "dead" while clients keep working, and what must the client do differently?

## serverVersion override + dead sentinel
**Path/Symbol:** `Comm._serverVersion: string|null` (`app/server/lib/Comm.ts:92–96`), `setServerVersion` :154–156, `setServerActivation` :162–164, consumed in `_onWebSocketConnection` :256 `serverVersion: this._serverVersion || version.gitcommit`.
**Signature:** `setServerActivation(active: boolean)` — active=false stores the literal string `"dead"`; null ⇒ report real gitcommit.
**Data Shape:** every clientConnect carries serverVersion; "dead" is a SENTINEL clients interpret as "this server is defunct — poll for a valid one".

### Decisive source
```ts
// For upgrading, we use this to set the server version for a defunct server
// to "dead" so that a client will know that it needs to periodically recheck
// for a valid server.
private _serverVersion: string | null = null;
...
public setServerActivation(active: boolean) {
  this._serverVersion = active ? null : "dead";
}
```

**Flow:** normal ops report `version.gitcommit` → rolling upgrade begins: operator flips activation off (or tests override via setServerVersion) → every NEW clientConnect reads serverVersion:"dead" → browser client sees dead ⇒ does NOT settle; periodically rechecks for a valid server → existing sockets stay up (no forced drop) → flip back or decommission.
**Invariant:** draining is COOPERATIVE at the application layer: the same message field doubles as version advertisement AND liveness sentence. Existing connections are never murdered by the drain path — only new admissions see "dead". Porters who force-close sockets during drain break in-flight work; porters who invent a separate field miss that clients already key off serverVersion.
**Probe:** deterministic source pins only (setServerActivation/setServerVersion have no dedicated spec in test/server/Comm.ts); behavior cross-referenced by client-side handling of serverVersion in app/client/components/GristWSConnection.ts — coverage caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "setServerActivation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sentinel-in-version-field draining pattern for any long-lived-socket service. Adapt the sentinel value/vocabulary. Omit Grist's gitcommit-as-version identity if you carry explicit versions.
