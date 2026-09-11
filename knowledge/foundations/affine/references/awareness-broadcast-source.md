<!-- capsule-v2 -->
# Awareness sync — ephemeral state with 'remote'-origin echo guard and connect-time self-announcement

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How are cursor/presence states synced without persistence, and how does a newcomer learn existing peers' presence?

## BroadcastChannelAwarenessSource
**Path/Symbol:** `blocksuite/framework/sync/src/awareness/impl/broadcast.ts`: whole class (:15-73); engine wrapper `blocksuite/framework/sync/src/awareness/engine.ts` (:5-18).
**Signature:** `connect(awareness: Awareness): void` / `disconnect(): void`; messages `{type:'connect'} | {type:'update', update: Uint8Array}`.
**Data Shape:** y-protocols Awareness states keyed by numeric clientID; outbound updates encode ONLY changed clientIDs (`encodeAwarenessUpdate(awareness, changedClients)`).

### Decisive source
```ts
handleAwarenessUpdate = (changes: AwarenessChanges, origin: unknown) => {
  if (origin === 'remote') return;                    // THE echo guard — inbound applies use 'remote'
  const changedClients = Object.values(changes).reduce((res, cur) => res.concat(cur));
  const update = encodeAwarenessUpdate(this.awareness!, changedClients);
  this.channel?.postMessage({ type: 'update', update });
};
// newcomer handshake: announce myself on join…
this.channel.postMessage({ type: 'connect' });
// …and answer EVERY other peer's announcement with MY OWN state
if (event.data.type === 'connect') {
  this.channel?.postMessage({ type: 'update',
    update: encodeAwarenessUpdate(this.awareness!, [this.awareness!.clientID]) });
}
```

**Flow:** `connect` opens the channel → posts `'connect'` → subscribes awareness 'update' + channel messages. Inbound `'update'` → `applyAwarenessUpdate(awareness, update, 'remote')` (origin string triggers the guard on the resulting local event). Inbound `'connect'` → reply with own client's state only. Engine (`AwarenessEngine.connect/disconnect`) fans the lifecycle out to N sources.

**Invariant:** (1) The guard is by CONVENTION — the literal string `'remote'` at both apply and check sites; renaming one side loops broadcasts forever. (2) Unlike doc sync there is NO clock/dedup layer: awareness is idempotent-by-timestamp semantics inside the protocol (states carry logical clocks in y-protocols), so duplicate/late delivery is safe but ordering is not guaranteed. (3) Replies to `'connect'` include ONLY the responder's own clientID — rebroadcasting known third-party states would create O(N²) message storms on every join. (4) `disconnect` closes the channel; y-protocols timeout handles ghost peers.

**Probe:** no dedicated unit spec upstream (consumer-tested caveat); pinned by source greps: `grep -c "type: 'connect'" blocksuite/framework/sync/src/awareness/impl/broadcast.ts` == 3 (type def, send, reply branch), and origin guard line `if (origin === 'remote') return;` :19-21. TestWorkspace wires it via `awarenessSources` (:76-86).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "BroadcastChannelAwarenessSource encodeAwarenessUpdate applyAwarenessUpdate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt origin-convention echo guard + announce-on-connect/answer-with-self handshake; adapt transport beyond BroadcastChannel; omit for servers that already run an awareness protocol endpoint.
