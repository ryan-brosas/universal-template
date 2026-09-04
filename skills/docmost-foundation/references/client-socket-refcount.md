<!-- capsule-v2 -->
# Client socket refcount — how does an SPA share one collab WebSocket across editors without tearing down live sessions?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How is the HocuspocusProviderWebsocket lifecycle managed when editor components mount and unmount at will?

## acquire/release with grace-period disconnect
**Path/Symbol:** `apps/client/src/features/editor/collab-socket.ts` (lines 1–46); consumer wiring `apps/client/src/features/editor/page-editor.tsx` (`HocuspocusProviderWebsocketComponent websocketProvider={socket}`, lines 142–158).
**Signature:** `acquireCollabSocket(): void`; `releaseCollabSocket(): void`; singleton via `getCollabSocket()`.
**Data Shape:** Module-level `socket`, `editorCount`, `releaseTimer`; `RELEASE_GRACE_MS = 5000`.

### Decisive source
```ts
export function releaseCollabSocket(): void {
  editorCount--;
  if (editorCount > 0) return;
  releaseTimer = setTimeout(() => {
    if (editorCount === 0) { socket?.disconnect(); }
  }, RELEASE_GRACE_MS);
}
```
Acquire cancels any pending release timer, bumps the count, sets `shouldConnect = true`, and connects only from `WebSocketStatus.Disconnected` — never while connecting/connected.

**Flow:** mount → acquire (cancel timer, count++, maybe connect) → unmount → release (count−−) → last out schedules disconnect in 5s → another editor mounts within grace → timer cancelled, socket reused.
**Invariant:** disconnect only fires if the count is STILL zero at timer fire — a mount/unmount/mount sequence must never drop the shared socket mid-session. The 5s grace absorbs route transitions where the old editor unmounts before the new one mounts.
**Probe:** `grep -cF 'RELEASE_GRACE_MS = 5000' apps/client/src/features/editor/collab-socket.ts` (=1), `grep -cF 'editorCount === 0' apps/client/src/features/editor/collab-socket.ts` (=1), `grep -cF 'autoConnect: false' apps/client/src/features/editor/collab-socket.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "acquireCollabSocket releaseCollabSocket HocuspocusProviderWebsocket", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt count + grace-timer sharing for any per-view realtime socket; adapt the grace duration; omit the React component glue. No upstream direct test; pinned by source read + probes.
