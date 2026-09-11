<!-- capsule-v2 -->
# Dual-channel event demux — when a WebRTC data channel AND a WebSocket sideband both deliver events, who wins?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** How do you run two live transports carrying the same event stream without duplicating or losing error events?

## Demux rule
**Path/Symbol:** `src/live/transport.ts:#handleServerEvent` (:353-362) vs `#handleSidebandEvent` (:342-351).
**Signature:** both `(payload: string): void` → parse → guarded callback fan-out.
**Data Shape:** Same parsed union from both channels; the sideband is authoritative once OPEN; the peer channel degrades to errors-only.

### Decisive source
```ts
// WebRTC peer (data channel):
const event = parseLiveServerEvent(payload);
if (!event || (this.#sideband?.readyState === WebSocket.OPEN && event.type !== "error")) return;
this.#options.callbacks.onEvent(event);

// Sideband (WebSocket): everything it parses is forwarded.
```

**Flow:** while the sideband is OPEN, peer frames are dropped EXCEPT `error` events (which always pass) — so transcript/audio flows over the sideband and transport-level failures can still surface from either pipe; before the sideband opens, the peer channel is the only source and forwards all.
**Invariant:** No duplicate delivery: exactly one channel owns normal-event forwarding at any time, selected by sideband readiness AT FRAME TIME; errors are exempt because they may originate on either channel. Callbacks are try/caught — UI exceptions never kill the transport loop.
**Probe:** `tests/live-controller.test.ts` + `tests/live-registration.test.ts` (event delivery through the composed controller; per-channel demux itself has no direct spec at this pin — caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "handleSidebandEvent handleServerEvent readyState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the readiness-gated primary-channel rule with errors-always-pass exemption. Adapt which physical channels play the roles. Omit the Codex signaling handshake that establishes them.
