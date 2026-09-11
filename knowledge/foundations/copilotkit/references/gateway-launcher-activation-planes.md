<!-- capsule-v2 -->
# Gateway launcher activation — how does a runtime start channels over a gateway and classify what activation failures mean?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** Given the realtime-gateway session primitives, how does the launcher wire control-vs-delivery planes at startup, and which failure shapes must a supervisor retry versus treat as configuration errors?

## Two-launcher split: with-gateway-control vs over-realtime-gateway
**Path/Symbol:** `packages/channels-intelligence/src/realtime-gateway-launcher.ts:startChannelsWithGatewayControl` (:130-238), `startChannelsOverRealtimeGateway` (:299-402).
**Signature:** `async function startChannelsOverRealtimeGateway(options): Promise<...>` — connects the control session (`connectRealtimeGateway`, declaring every adapter pair per channel), then starts a `ChannelDeliveryTransport` on top.
**Data Shape:** join declaration = `{protocol, runtimeInstanceId, channels: [{channelName, adapter}]}`; provider states read back via `session.providerStates()`.

### Decisive source
```typescript
// (launcher region :299-402) shape of the composition:
const session = await connectRealtimeGateway({
  wsUrl, apiKey, projectId,
  join: { protocol: CHANNEL_DELIVERY_PROTOCOL,
          runtimeInstanceId,
          channels: declaredAdapters },      // slack AND teams pairs unconditionally
});
const transport = new ChannelDeliveryTransport({ session, runtimeInstanceId, ... });
transport.start(handler);
// health + attachment surface to supervisors:
session.onStateChange((state, detail) => ...);   // online / reconnecting / gave_up
session.providerStates();                        // attached / unhealthy / not_attached / ...
```

**Flow:** build the unconditional adapter declaration per channel → open the CONTROL session (join settles before the promise resolves; invitations buffered meanwhile) → wrap it in the delivery transport (claim/join/packet machinery from the transport capsules) → hand supervisors BOTH signals: connection health (`onStateChange`) for "can we send", provider states (`providerStates()`) for "is the provider actually bound" — two different questions that must not be conflated. `startChannelsWithGatewayControl` is the variant where an EXISTING gateway control plane already owns coordination and only delivery rides this socket.
**Invariant:** The two status planes compose but never substitute: `reconnecting` says nothing about whether Slack is bound, and `attached` says nothing about the current socket. Retry classification keys off typed errors: `RealtimeGatewayUnreachableError.retryable=false` (NXDOMAIN-class) ⇒ stop, config error; `retryable=true` or `GATEWAY_JOIN_FAILED` with `gateway_draining` ⇒ retry with backoff.
**Probe:** `packages/channels-intelligence/src/realtime-gateway.test.ts` :248 "joins the channel topic with declared channels and disconnects"; `realtime-gateway-launcher.ts` deterministic anchor `grep -n "startChannelsOverRealtimeGateway" packages/channels-intelligence/src/realtime-gateway-launcher.ts`. Coverage caveat: no dedicated launcher test file at this pin; behavior pinned via gateway + transport suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "startChannelsOverRealtimeGateway startChannelsWithGatewayControl ChannelDeliveryTransport", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-plane status separation for any managed-channel runtime. Adapt declaration building to your adapter registry. Omit either status plane and your dashboard will conflate "socket down" with "provider misconfigured".
