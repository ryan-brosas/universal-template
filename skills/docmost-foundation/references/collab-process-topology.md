<!-- capsule-v2 -->
# Collab process topology — how does docmost run the realtime server as a SEPARATE process from the API?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How is a second Nest app bootstrapped for WebSockets only, and how does it shut down without losing buffered Yjs state?

## collab-main bootstrap + graceful destroy choreography
**Path/Symbol:** `apps/server/src/collaboration/server/collab-main.ts` (lines 12–45); `apps/server/src/collaboration/collaboration.gateway.ts`:`destroy` (lines 170–192); `apps/server/src/collaboration/adapter/collab-ws.adapter.ts`:`handleUpgrade` (lines 10–31); stats gate in `apps/server/src/collaboration/server/collab-app.module.ts` (lines 45–50).
**Signature:** `destroy(collabWsAdapter: CollabWsAdapter): Promise<void>`; root scripts `pnpm collab` / `collab:prod` (separate entrypoint from `pnpm start`).
**Data Shape:** WS endpoint at path `/collab`; optional stats controller gated by env `COLLAB_SHOW_STATS=true`.

### Decisive source
```ts
await new Promise(async (resolve) => {
  this.hocuspocus.configuration.extensions.push({
    async afterUnloadDocument({ instance }) {
      if (instance.getDocumentsCount() === 0) resolve('');
    },
  });
  collabWsAdapter?.close();               // stop accepting upgrades
  if (this.hocuspocus.getDocumentsCount() === 0) resolve('');
  this.hocuspocus.closeConnections();
  this.hocuspocus.flushPendingStores();   // push debounced writes NOW
});
await this.hocuspocus.hooks('onDestroy', { instance: this.hocuspocus });
```
Adapter routes by pathname — `/collab` upgrades to its own noServer WebSocketServer, `/socket.io/` is ignored, everything else gets `socket.destroy()`.

**Flow:** SIGTERM → shutdown hook → close listener → closeConnections + flushPendingStores (drains every doc's debounce buffer immediately) → per-document unload hooks fire as docs drain → resolver fires on last unload → onDestroy runs (redis-sync disconnects pub/sub).
**Invariant:** flushPendingStores MUST precede process exit or recently-typed content inside the 10s debounce window is lost; the promise resolves either via the afterUnloadDocument latch OR the already-empty check, whichever comes first. The adapter must NOT destroy unknown upgrade paths silently with success — unknown paths get socket.destroy(), only /socket.io/ is passed over.
**Probe:** `grep -cF "private path = '/collab';" apps/server/src/collaboration/collaboration.module.ts` (=1), `grep -cF 'COLLAB_SHOW_STATS' apps/server/src/collaboration/server/collab-app.module.ts` (=1), `grep -cF 'flushPendingStores' apps/server/src/collaboration/collaboration.gateway.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "collab main bootstrap destroy flushPendingStores handleUpgrade", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt separate-process realtime tier + drain-then-exit shutdown ordering; adapt port/env plumbing; omit Fastify/Nest specifics. No upstream direct test; pinned by source read + probes.
