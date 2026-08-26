<!-- capsule-v2 -->
# Channel listing staleness grammar — how does the channels view decide what is "active" for three channel kinds?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What per-kind rules classify channels as active vs stale?

## memory always-on · named by last event · session by agents-then-feed
**Path/Symbol:** `handlers/coordination/channels.ts:formatChannelLine` (:22-90), `executeChannels` (:92-156); constants `channel.ts:ACTIVE_THRESHOLD_MS = 30min` (:33), `MEMORY_CHANNEL_ID` (:30).
**Signature:** `formatChannelLine(channel, dirs, state, now): { line, active }`.
**Data Shape:** reference timestamp = last feed event `ts`, else header createdAt; threshold 30min.

### Decisive source
```ts
// #memory is always active (cross-session by design)
if (channel.type === 'named' && channel.id === 'memory') return { ..., active: true };
if (channel.type === 'named') {
  const lastTs = getLastActivity(dirs, channel.id);
  const referenceTs = lastTs ?? channel.createdAt;
  const isActive = now - new Date(referenceTs).getTime() < ACTIVE_THRESHOLD_MS;
  ...
}
// Session: check for agents
const agents = store.getAgentsInChannel(state, dirs, channel.id);
if (agents.length > 0) return { ...'N agents · names', active: true };
const lastTs = getLastActivity(dirs, channel.id);   // then recent-feed fallback
```

**Flow:** listChannels sorts by id; each line classified by kind; output splits Active section first with inactive collapsed behind `--all` plus a count line. Named channels fall back to createdAt as their activity clock; sessions prefer LIVE presence over feed recency.
**Invariant:** The memory-channel exemption is hard-coded by id+type — porters who rename #memory lose the always-active guarantee. Session classification order matters: presence beats recency (an idle-but-populated session shows its roster, not "idle").
**Probe:** direct tests `tests/swarm/channels.test.ts::shows active named channels and #memory as always active` (:109), `::hides stale named channels by default (except #memory)` (:127), `::shows session channels with live agents as active` (:166), `::returns empty when no channels exist` (:240); `grep -n "cross-session by design" handlers/coordination/channels.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "formatChannelLine executeChannels ACTIVE_THRESHOLD_MS getLastActivity getAgentsInChannel", limit: 5 });
```

## Verdict
Adopt the per-kind classification trio and the always-on sentinel channel; adapt threshold and rendering; keep presence-over-recency ordering for session channels.
