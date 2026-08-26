<!-- capsule-v2 -->
# Sticky gave_up connection-health FSM — how does a manager's status stop flapping while Phoenix retries a dead link?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** Phoenix auto-retries forever — how should the public health state transition between online / reconnecting / gave_up so failed retries don't flap and transient outages still self-heal?

## Sticky-latch state machine with episode re-arming
**Path/Symbol:** `packages/channels-intelligence/src/realtime-gateway.ts:connectRealtimeGateway` health block (:826-930); transitions `enterReconnecting` (:882-901), `enterOnline` (:902-919), `emitState` (:867-881); latch `gaveUp` (:849), window timer (:846); late-subscriber replay in returned session (:1138-1155).
**Signature:** `onStateChange(cb: (state: "online"|"reconnecting"|"gave_up", detail?: { reason?: string; code?: string }) => void): void`.
**Data Shape:** window = `reconnectGiveUpMs` (default 60s) armed on the FIRST drop of an outage; detail cause prefers the per-outage probe verdict (`lastOutageDiagnosis`) over raw transport text.

### Decisive source
```typescript
const enterReconnecting = (): void => {
  if (closingIntentional) return;
  // Sticky give-up: once the window has fired we stay `gave_up` while Phoenix
  // keeps retrying a dead link ... Only a successful rejoin (`enterOnline`)
  // clears the latch and re-arms the window for a genuinely fresh drop.
  if (gaveUp) return;
  if (giveUpTimer === undefined) {          // arm ONCE per outage episode
    giveUpTimer = setTimeout(() => {
      giveUpTimer = undefined;
      gaveUp = true;
      emitState("gave_up");
    }, giveUpMs);
    (giveUpTimer as unknown as { unref?: () => void }).unref?.();
  }
  emitState("reconnecting");
};
const enterOnline = (): void => {
  gaveUp = false;
  clearGiveUpTimer();
  outageEpisode += 1;                       // late probes can't misattribute
  outageProbe = undefined;
  lastOutageDiagnosis = undefined;
  lastTransportError = undefined;
  lastTransportCode = undefined;
  emitState("online");
};
```

**Flow:** socket-level OR channel-level drop (Phoenix can error a channel while the socket stays open — both routes funnel into one deduped transition) → `reconnecting`, window armed once → failed retries during the SAME outage are absorbed by the sticky latch → window elapses → `gave_up` (manager maps to error; NOT terminal) → a later SUCCESSFUL rejoin → `online`, latch cleared, window re-armed, outage evidence wiped so the NEXT outage diagnoses itself. `emitState` never repeats the same state, skips everything after intentional teardown, and isolates throwing observers. Late subscribers replay current non-online state at registration.
**Invariant:** "Back online" comes from a successful REJOIN (the join-push `"ok"` hook re-fires because Phoenix `Push.resend` preserves `recHooks`), NEVER from the socket merely reopening — channels may still be down. Episode counters keep slow probes from latching this outage's cause onto the next one.
**Probe:** `packages/channels-intelligence/src/realtime-gateway.test.ts` :690 "gives up (emits gave_up)..."; :719 "recovers to online after gave_up... not terminal"; :756 "keeps gave_up sticky until a successful rejoin, then re-arms (OSS-473)"; :1320 "does not attribute a later outage to the previous one's cause". Deterministic anchor `grep -n "let gaveUp" packages/channels-intelligence/src/realtime-gateway.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "enterReconnecting enterOnline gaveUp emitState onStateChange", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sticky latch + re-arm-on-heal FSM over any auto-reconnecting transport. Adapt windows/default timeouts to your SLO. Omit socket-open as an "online" signal — that is the exact bug this machine exists to prevent.
