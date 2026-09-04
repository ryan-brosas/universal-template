<!-- capsule-v2 -->
# WSChannel custom-event hook — how is arbitrary websocket traffic recorded with bounded payload sizes?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What limits and message shape apply when users pipe their own socket data into the session?

## 5 MB data / 255-char name, direction-tagged envelope
**Path/Symbol:** `tracker/tracker/src/main/app/index.ts` — `App.trackWs(channelName)` (:1872–1885); public passthrough `API.trackWs` (`main/index.ts:361–366`); wire builder `WSChannel('websocket', channel, data, timestamp, dir, msgType)` from messages.gen.
**Signature:** `trackWs(channel: string): (msgType: string, data: string, dir?: 'up'|'down') => void`.
**Data Shape:** validation: `typeof msgType==='string' && typeof data==='string' && data.length ≤ 5*1024*1024 && msgType.length ≤ 255`; anything failing is silently dropped.

### Decisive source
```ts
return (msgType: string, data: string, dir: 'up' | 'down' = 'down') => {
  if (typeof msgType !== 'string' || typeof data !== 'string' ||
      data.length > 5 * 1024 * 1024 || msgType.length > 255) { return }
  this.send(WSChannel('websocket', channel, data, this.timestamp(), dir, msgType))
}
```

**Flow:** integrator wraps their socket handler → each event becomes a WSChannel message stamped with tracker time → rides the normal batch pipeline (player stream). Direction distinguishes client-sent vs server-sent for replay arrows.
**Invariant:** Drop silently — a recording hook must never throw into the host app's socket handler. Timestamp uses `this.timestamp()` (delay-corrected), not Date.now().
**Probe:** `grep -c "data.length > 5 \* 1024 \* 1024" tracker/tracker/src/main/app/index.ts` → `1`; `grep -c 'WSChannel' tracker/tracker/src/main/app/index.ts` → `2`. Direct tests: none upstream for trackWs (grep-pinned).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "trackWs WSChannel channel msgType direction", limit: 10 });
```

## Verdict
Adopt bounded drop-silently hooks. Adapt size caps. Omit direction tagging if unidirectional.
