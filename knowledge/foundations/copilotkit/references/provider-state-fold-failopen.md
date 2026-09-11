<!-- capsule-v2 -->
# Provider-state fold & fail-open parsing — how does a runtime report "is a provider actually attached" without lying, and what happens when the gateway says nothing?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** The launcher declares EVERY supported adapter per channel — how does the five-state attachment vocabulary fold into one truthful status, and why must an unparseable reply degrade to `undefined` rather than "not attached"?

## BEST-of adapter fold over a duck-typed cross-package seam
**Path/Symbol:** `packages/channels-intelligence/src/realtime-gateway.ts:ChannelProviderState` (:51-56), `PROVIDER_STATES` (:76-82), `parseChannelProviderStates` (:97-112), getter `providerStates()` (:553-563); consumer twin `PROVIDER_LEGS`/`foldChannelLegs` in `packages/runtime/src/v2/runtime/core/channel-manager.ts`.
**Signature:** `function parseChannelProviderStates(reply: unknown): ChannelProviderStates | undefined`; states = `attached | unhealthy | not_attached | disabled | channel_not_declared`.
**Data Shape:** control-join reply carries optional `channels: Record<name, state>`; parsed result is per-declared-channel; unknown values dropped INDIVIDUALLY.

### Decisive source
```typescript
// A Runtime declares EVERY supported adapter per Channel (the launcher emits a
// `slack` and a `teams` pair unconditionally), so the Gateway folds the adapter
// states BEST-of — attached > unhealthy > not_attached — answering "is at least
// one provider bound?". A correctly configured Slack-only Channel is therefore
// `attached`, not dragged to `not_attached` by the Teams adapter nobody asked
// for. (:43-49)
export function parseChannelProviderStates(reply: unknown): ChannelProviderStates | undefined {
  if (typeof reply !== "object" || reply === null) return undefined;
  const raw = (reply as { channels?: unknown }).channels;
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) return undefined;
  const states: Record<string, ChannelProviderState> = {};
  for (const [name, value] of Object.entries(raw)) {
    if (typeof value === "string" && PROVIDER_STATES.has(value)) {
      states[name] = value as ChannelProviderState;
    }
  }
  return Object.keys(states).length > 0 ? states : undefined;
}
```
```typescript
// Adding a state here needs the same addition in runtime/channel-manager.ts's
// PROVIDER_LEGS + a case in foldChannelLegs. Until both land, the new state
// fails open to `unknown` on the consuming side — the Channel keeps its
// transport-derived status rather than being wrongly certified or condemned.
// Safe, but silent. (:66-74)
```

**Flow:** control join replies → parse drops unknown/malformed entries one by one → absent key, malformed map, or zero valid entries ALL yield `undefined` ("gateway did not tell us") → consumers degrade to transport-derived status instead of certifying or condemning any channel → the getter re-reads the newest join reply, so Phoenix auto-rejoins refresh provider state for free (a channel provisioned during an outage reports `attached` after the next rejoin).
**Invariant:** `undefined` ≠ "no provider attached": a pre-contract gateway and a gateway with a failed DB read both omit the key and must NOT be shown as unprovisioned. `attached` requires the adapter's own `status === "active"` INSIDE the predicate — reporting attachment for a draft/disabled/error adapter just reintroduces the false green one state later.
**Probe:** `packages/channels-intelligence/src/realtime-gateway.test.ts` :1445 "exposes the provider states the gateway reported"; :1467 "reports undefined when the gateway sends no channels map"; :1497 "refreshes provider states from the rejoin reply after a transport drop". Deterministic anchor `grep -n "channel_not_declared" packages/channels-intelligence/src/realtime-gateway.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "parseChannelProviderStates ChannelProviderState foldChannelLegs providerStates", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fail-open-to-undefined semantics for optional capability reports crossing version boundaries. Adapt the state set to your domain but mirror it in BOTH packages when the seam is dependency-free by design. Omit the best-of fold and every multi-adapter channel reports permanently degraded health.
