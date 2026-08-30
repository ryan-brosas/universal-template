<!-- capsule-v2 -->
# Cluster custom-event RPC — how does a REST-side caller run a mutation on whichever server owns the doc?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How do you invoke a named handler against a Yjs document that may be loaded on another instance, with request/response semantics over pub/sub?

## customEventStart / customEventComplete with replyId + TTL
**Path/Symbol:** `apps/server/src/collaboration/extensions/redis-sync/redis-sync.extension.ts`:`handleEvent` / `handleEventLocally` (lines 265–311, 254–263); handler map in `apps/server/src/collaboration/collaboration.handler.ts`:`getHandlers` (lines 22–116).
**Signature:** `handleEvent<TName>(eventName: TName, documentName: string, payload: any, onlyIfOpen = false): Promise<ReturnType<TCE[TName]>>`.
**Data Shape:** `{type:'customEventStart', eventName, documentName, payload, replyTo, replyId}` to owner channel; reply `{type:'customEventComplete', replyId, payload}`. `customEventTTL` default 30s. `onlyIfOpen=true` reads the lock WITHOUT claiming (`getLock`) and returns undefined when no live owner.

### Decisive source
```ts
if (proxyTo && proxyTo !== this.serverId) {
  ++this.replyIdCounter;
  const proxyMessage: RSAMessageCustomEventStart = { eventName, documentName, payload, replyTo: `${this.msgChannel}:${this.serverId}`, replyId, type: 'customEventStart' };
  this.pub.publish(`${this.msgChannel}:${proxyTo}`, msg);
  const { promise, resolve, reject } = Promise.withResolvers();
  this.pendingReplies[replyId] = resolve;
  setTimeout(() => {
    delete this.pendingReplies[replyId];
    reject(new Error('TIMEOUT'));
  }, this.customEventTTL);
  return promise;
}
```

**Flow:** local doc? run directly : (onlyIfOpen ? getLock : claim) → owner executes `handleEventLocally`, publishes complete → caller resolves by replyId; TTL timer rejects and deletes the pending entry.
**Invariant:** reply correlation is by numeric `replyId` scoped to one server process; every pending entry MUST have a TTL-backed rejection so a lost pub/sub message can't leak the promise forever. The three shipped handlers (`setCommentMark`, `resolveCommentMark`, `updatePageContent`) all mutate through `withYdocConnection` — never touch the Y.Doc outside an openDirectConnection transact.
**Probe:** `grep -cF 'Promise.withResolvers()' apps/server/src/collaboration/extensions/redis-sync/redis-sync.extension.ts` (=1) and `grep -cF "doc.getXmlFragment('default')" apps/server/src/collaboration/collaboration.handler.ts` (=4).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "handleEvent customEventStart pendingReplies customEvents", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the start/complete envelope with per-call replyId + TTL rejection as the portable remote-mutation RPC; adapt payload serialization; omit the hocuspocus direct-connection mechanics if your runtime exposes another transactional doc handle. No upstream direct test; pinned by source read + probes.
