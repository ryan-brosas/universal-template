<!-- capsule-v2 -->
# Delivery ID grammar — why is a provider reference NOT a message id, and why must packets stay destination-free?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** What are the exact identifier/packet shapes crossing the gateway boundary, and which fields would turn a safe packet into a credential leak?

## Opaque capability vs correlation-id split + exact-field packet validation
**Path/Symbol:** `packages/channels-intelligence/src/delivery-contracts.ts` — patterns :17-21, `assertProviderReference`/`isProviderReference` (:154-172), `assertProviderMessageId` (:175-193), `assertDeliveryPacket` (:208-244), payload switch `isDeliveryPayload` (:246-401), `hasExactFields` (:407-418), bounds `DELIVERY_PACKET_MAX_BYTES` :15 / `CHANNEL_DELIVERY_JOIN_TOKEN_TTL_SECONDS` :9.
**Signature:** `function assertDeliveryPacket(value: unknown): asserts value is ChannelDeliveryPacket`; `PROVIDER_REFERENCE_PATTERN = /^pref_v1_[A-Za-z0-9_-]{8,4088}$/`; `PROVIDER_MESSAGE_ID_PATTERN = /^pid_v1_[A-Za-z0-9_-]{43}$/`.
**Data Shape:** packet = protocol + deliveryId(`dlv_`) + runtimeInstanceId(`rti_`) + ownerGeneration(int ≥1) + seq(int ≥0) + packetId(`pkt_`) + one payload variant; every string field byte/length-bounded (text ≤40,000; blocks ≤100; cards ≤25; reactions ≤128 UTF-8 bytes).

### Decisive source
```typescript
export function assertProviderReference(value: unknown): asserts value is string {
  if (typeof value !== "string" || !PROVIDER_REFERENCE_PATTERN.test(value)) {
    throw new TypeError("provider reference must be an opaque pref_v1 capability");
  }
}
// A provider message id is a STABLE, NON-CAPABILITY correlation id:
if (typeof value !== "string" || !PROVIDER_MESSAGE_ID_PATTERN.test(value)) {
  throw new TypeError("provider message id must be a stable pid_v1 correlation id");
}

if (deliveryPacketByteLength(value) > DELIVERY_PACKET_MAX_BYTES) {   // 64 KiB
  throw new RangeError("delivery packet exceeds 64 KiB");
}
```
```typescript
test("rejects trusted addressing and credentials", () => { /* per-packet to/channel/token shapes */ });
test("rejects per-packet auth and heartbeat shapes", () => { /* auth/heartbeat fields never legal */ });
```

**Flow:** runtime builds provider effects tagged by `kind` (`slack.*` / `teams.*` / commit / terminal) → `buildPacket` stamps identity + seq → `assertDeliveryPacket` enforces exact-field sets (no extra, none missing), per-kind bounded strings/arrays, shared UTF-8 reaction bound, 64KiB cap → gateway acks with phase + result carrying ONLY opaque handles → any `providerReference` in a result must re-validate as `pref_v1_*`, any echoed message id as `pid_v1_*`.
**Invariant:** `pref_v1_` references are opaque, delivery-scoped CAPABILITIES (possession = right to act); `pid_v1_` ids are stable CORRELATION ids — swapping them lets a client replay someone else's capability or breaks idempotent retries. Packets are DESTINATION-FREE: no addresses, credentials, auth, or heartbeat fields ever ride the wire shape — the test suite pins each forbidden shape explicitly.
**Probe:** `packages/channels-intelligence/src/delivery-contracts.test.ts` :51 "rejects trusted addressing and credentials"; :223 "rejects per-packet auth and heartbeat shapes"; :238 "enforces the shared identifier and provider-reference bounds"; :263 "rejects packets over 64 KiB". Deterministic anchor `grep -c "assertProviderReference" packages/channels-intelligence/src/delivery-contracts.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "ChannelDeliveryPacket assertProviderReference assertDeliveryPacket hasExactFields", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capability/correlation-id split and exact-field validation for ANY cross-trust-boundary effect protocol. Adapt prefixes/bounds to your namespace. Omit the destination-free rule and every downstream consumer inherits an address-spoofing surface.
