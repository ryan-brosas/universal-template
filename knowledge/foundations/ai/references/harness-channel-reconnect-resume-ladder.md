<!-- capsule-v2 -->
# SandboxChannel reconnect ladder — how does a mid-turn socket drop become invisible to the consumer?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** What state machine lets a host-side WebSocket wrapper reconnect, replay, and flush without the in-flight turn's consumer ever observing the blip — and when must a drop finally surface as close?

## Elapsed-budget backoff loop + stale-socket guard
**Path/Symbol:** `packages/harness/src/utils/sandbox-channel.ts` — `SandboxChannel.reconnectLoop` (:363–419), `wire` stale-drop guard (:335–347), `rawSend`/`flushPending` (:421–433), serialized dispatch chain (`enqueue` :435–437), defaults (:179–181).
**Signature:** `reconnect?: { maxElapsedMs? = 30_000; initialDelayMs? = 50; maxDelayMs? = 2_000 }`; `onReconnect(handler): () => void`.
**Data Shape:** lifecycle flags `connected / closing / suspended / terminal`; `pendingSends: string[]`; `_lastSeenEventId: number`.

### Decisive source
```ts
// sandbox-channel.ts:376 — re-check the world AFTER connecting
const ws = await this.connectThunk();
if (this.terminal || this.closing) {
  try { ws.close(); } catch {} return;      // don't wire a socket into a dead channel
}
this.wire(ws); this.ws = ws; this.connected = true;
this.rawSend(JSON.stringify({ type: 'resume', lastSeenEventId: this._lastSeenEventId }));
this.flushPending();                        // queued sends AFTER resume, in order
for (const handler of this.onReconnectHandlers) handler();
...
} catch (cause) {
  if (Date.now() - start >= this.maxElapsedMs) {
    this.finalizeClose(1006, 'reconnect failed'); ... return;
  }
  await sleep(delay);                       // unref'd timer
  delay = Math.min(delay * 1.5, this.maxDelayMs);
}
// wire(): if (ws !== this.ws) return;  ← a late drop of an OLD socket is inert
```

**Flow:** drop → `onDrop` enqueues `reconnectLoop` on the dispatch chain (a close can never overtake an in-dispatch message) → attempts with ×1.5 backoff capped at 2s inside an ELAPSED-TIME budget (not attempt count) → success rewires + sends `resume{lastSeenEventId}` + flushes pending sends + fires onReconnect → consumer sees zero events lost, zero duplicates. `beginClose()` before a deliberate close flips the next drop from "reconnect" to "terminal".
**Invariant:** A transient drop NEVER fires `onClose`; budget exhaustion finalizes exactly once with code 1006 reason `'reconnect failed'`; open() itself is single-attempt (startup failures reject so `doStart` fails cleanly — retries apply only to drops AFTER a successful open); every inbound frame (including schema-invalid ones) still advances `_lastSeenEventId` monotonically.
**Probe:** direct tests `packages/harness/src/utils/sandbox-channel.test.ts:235–277` ("reconnects transparently on a transient drop" — fresh socket's first sent frame IS `{type:'resume',lastSeenEventId:2}`, `closes` stays empty), :279–294 ("queues host → bridge sends while disconnected" — order `[resume, abort]`), :308–321 (drop after beginClose ⇒ no second socket), :323–345 (budget exhausted ⇒ onClose 1006).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "SandboxChannel reconnectLoop flushPending", limit: 5 });
// verified live @9d9a73f — SandboxChannel.reconnectLoop :363-419 rank#1; rawSend :421-427; flushPending :429-433
```

## Verdict
Adopt elapsed-time-budget reconnect with post-connect state re-check and resume-then-flush ordering for any long-lived runtime socket; adapt delays/budget to your SLA (upstream: 50ms→2s over 30s); omit onDebug telemetry if you have no diagnostics sink. Companion: harness-channel-suspend-cursor-freeze.md owns how suspension differs from a drop.
