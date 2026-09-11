<!-- capsule-v2 -->
# ws-send-failure-funnel — When a send to a live websocket fails, what happens to the message and to the connection?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** Distinguish sendMessage from sendMessageOrInterrupt — which failures queue, which interrupt, and what does a queued message cost?

## Two-tier send policy
**Path/Symbol:** `app/server/lib/Client.ts:sendMessage` (:243–311) + `sendMessageOrInterrupt` (:231–238); caller split: method responses use OrInterrupt (:539), broadcastMessage uses `.catch(() => {})` (`Comm.ts:127–131`).
**Signature:** `sendMessage(messageObj)` = never throws for transport reasons (queues instead); `sendMessageOrInterrupt(messageObj)` = on send error, log + `interruptConnection()`.
**Data Shape:** three failure postures coexist: QUEUE-and-continue (default), INTERRUPT-connection (request responses), DROP-silently (broadcasts).

### Decisive source
```ts
public async sendMessageOrInterrupt(messageObj): Promise<void> {
  try { await this.sendMessage(messageObj); }
  catch (e) { this._log.error(null, "sendMessage error", e); this.interruptConnection(); }
}
```

**Flow:** sendMessage: destroyed ⇒ silent no-op → reserve memory → stamp seqId → stringify → live socket? try `_sendToWebsocket`; success ⇒ done ("A successful send does NOT mean the message was received" — in-source note points at ack-based designs they deliberately did not build) ; send THROWS ⇒ fall through to queue → no socket or throw ⇒ ledger (budget-guarded; overflow boots client) → OrInterrupt wrapper: any residual throw ⇒ interrupt (strip listeners, keep one onerror, terminate).
**Invariant:** request/response traffic uses the interrupting wrapper so a wedged socket cannot silently swallow answers (client would wait forever) — but the underlying send still prefers queuing over throwing. Fire-and-forget broadcasts drop errors entirely by design. The comment chain documents why ack-until-received was rejected: it changes the reconnect contract and Grist instead accepts "more likely to be lacking messages on reconnect, having to reset".
**Probe:** `test/server/Comm.ts:364/:367` (send-fail ⇒ queued then delivered on reconnect), :519 ("deliver a response prepared while the connection was down").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "sendMessageOrInterrupt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-posture send taxonomy keyed to caller semantics (response=interrupting, async=queueing, broadcast=dropping). Adapt thresholds. Omit the Azure ack-based alternative unless you need stronger-than-at-most-once delivery.
