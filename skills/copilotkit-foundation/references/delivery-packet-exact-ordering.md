<!-- capsule-v2 -->
# Delivery packet path — how do ordered, exactly-acked packets survive reconnects without duplicating or skipping a sequence?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** A delivery streams provider effects over a flaky socket with one-use join tokens — what is the exact enqueue/ack/reconnect contract that keeps seq strictly ordered and the SAME packet retried?

## Tail-chained enqueue + exact-ack validation + capability-aware resend
**Path/Symbol:** `packages/channels-intelligence/src/delivery-transport.ts:ClaimedChannelDelivery` (:263-764): `enqueue` (:591-637), `buildPacket` (:639-658), `sendExactPacket` (:660-720), `assertExactAcknowledgement` (:722-763); state fields `nextSeq`/`tail`/`unacknowledgedPacket` (:264-267).
**Signature:** `private enqueue(payload: ChannelDeliveryPayload, bestEffort = false): Promise<Record<string, unknown>>`; `effect(_responseId, payload, options?: { charge?: boolean; bestEffort?: boolean })`.
**Data Shape:** packet = `{protocol:"channel_delivery_v1", deliveryId, runtimeInstanceId, ownerGeneration, seq, packetId, payload}` ≤64KiB; ack = `{deliveryId, seq, packetId, phase: applied|retry_wait|failed|uncertain, retryAt?, result}`.

### Decisive source
```typescript
const operation = this.tail.then(async () => {
  if (this.terminalApplied) throw new Error(`... packet path is closed`);
  if (!isCleanupPacket && this.effectsClosed) throw new Error(`... packet path is closed`);
  const packet = this.buildPacket(payload);
  this.unacknowledgedPacket = packet;
  try {
    const acknowledgement = await this.sendExactPacket(packet);
    this.assertExactAcknowledgement(packet, acknowledgement);
    this.unacknowledgedPacket = undefined;
    this.nextSeq += 1;                    // seq advances ONLY after exact ack
    return acknowledgement.result;
  } catch (error) {
    this.unacknowledgedPacket = undefined;
    if (!isCleanupPacket && !bestEffort && payload.kind !== "slack.thread.status") {
      this.effectsClosed = true;          // permanent failure seals effects...
    }                                     // ...but terminal + stream.stop stay sendable
    throw error;
  }
});
this.tail = operation.catch(() => undefined);
```
```typescript
// sendExactPacket: same packet retried across soft transport failures
attempt += 1;
const delayMs = Math.min(5_000, 50 * 2 ** Math.min(attempt, 6)); // capped backoff
await waitUnlessStopped(delayMs, this.signal);
if (Date.now() >= Date.parse(this.delivery.deliveryExpiresAt)) break;
const refreshed = await this.reconnect();       // fresh one-use join token
// legacy gateways: strip fullText unless rejoin re-declared the capability
if (packet.payload.kind === "slack.stream.append" && packet.payload.fullText !== undefined &&
    !refreshed.capabilities?.includes(SLACK_STREAM_APPEND_FULL_TEXT_CAPABILITY)) {
  const { fullText: _fullText, ...legacyPayload } = packet.payload;
  pendingPacket = { ...packet, payload: legacyPayload };
}
```

**Flow:** every packet chains on `tail` (strict per-delivery FIFO; the chain never rejects) → build validates adapter-prefix + full grammar → push → ack must match deliveryId+seq+packetId EXACTLY (conflicting ack throws) and `retry_wait` ⇔ `retryAt` present → only then does `nextSeq` advance → soft failures (not stopped/push-error/permanent-TypeError) back off (cap 5s), mint a fresh token via `reconnect()`, refresh ownerGeneration + expiry + capabilities on the SAME packet → loop until `deliveryExpiresAt`, else "ownership expired".
**Invariant:** Exactly-once ordering lives client-side: seq increments only after an exact ack; retries always resend the IDENTICAL packet (same seq/packetId). Cleanup packets (`terminal`, `*.stream.stop`) bypass `effectsClosed` so providers never see an open native stream or a missing terminal.
**Probe:** `packages/channels-intelligence/src/delivery-transport.test.ts` :1048 "retries the exact packet after reconnect and calls no second sequence"; :1096 "polls the same packet after a retry-wait result"; :1310 "refreshes owner generation on packets after reconnect"; :1379 "still allows stream.stop after a permanent non-terminal failure"; :471 "rejects acknowledgement fields that drift from the strict Gateway schema". Deterministic anchor `grep -n "nextSeq += 1" packages/channels-intelligence/src/delivery-transport.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "ClaimedChannelDelivery enqueue sendExactPacket assertExactAcknowledgement", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tail-chain + exact-ack + identical-packet-retry trio for any ordered effect stream over lossy transports. Adapt the capability-strip rule to your negotiation surface. Omit the effects-sealed exception for cleanup packets and streams will leak.
