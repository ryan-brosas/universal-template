<!-- capsule-v2 -->
# Replay playability normalization — how do you decide a recording is playable and repair timestamps so rrweb-player never crashes?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** What makes an events array replayable, and how are missing/monotone-violating timestamps synthesized?

## replay-playability-normalization
**Path/Symbol:** `src/lib/replay.ts:hasReplayableFullSnapshot :111-125, getReplayPlayerEvents :176-208, canReplayEvents :210-212`; direct tests `src/lib/replay.test.ts:27-83`.
**Signature:** `getReplayPlayerEvents(events) -> normalized[]` (≥2 events or []); playable = some FullSnapshot(type 2) with `Number.isInteger(node.type) && Array.isArray(node.childNodes)`.
**Data Shape:** non-finite/missing timestamps become `lastTimestamp + 1` synthetic increments; single-event arrays are DUPLICATED with +1 timestamp.

### Decisive source
```ts
if (!hasReplayableFullSnapshot(replayEvents)) return [];    // no usable snapshot ⇒ unplayable
const firstTimestamp = replayEvents.map(getReplayTimestamp).find(t => t !== null) ?? Date.now();
let lastTimestamp = firstTimestamp - 1;
const normalizedEvents = replayEvents.map(event => {
  const timestamp = getReplayTimestamp(event);
  if (timestamp !== null) { lastTimestamp = timestamp; return event; }
  lastTimestamp += 1;                                        // synthesize monotone clock
  return { ...event, timestamp: lastTimestamp };
});
if (normalizedEvents.length === 1) {
  return [normalizedEvents[0], { ...normalizedEvents[0], timestamp: normalizedEvents[0].timestamp + 1 }];
}
```

**Flow:** filter typeless junk → require structural FullSnapshot (not just type===2: node payload must exist) → walk events carrying the last REAL timestamp forward, filling gaps with +1ms → pad singleton recordings to two events.
**Invariant:** rrweb-player requires ≥2 distinct timestamps; the duplicate-singleton trick is cheaper than special-casing the player. Timestamps must be NON-DECREASING — real ones advance `lastTimestamp`, only holes synthesize, so ordering is preserved even in mixed arrays.
**Probe:** `grep -c "test(" src/lib/replay.test.ts` → 10 (:44 usable-snapshot check, :56 player normalization, :76 negative case, :80 null-input safety).
**Probe:** `grep -n "canReplayEvents requires" src/lib/replay.test.ts` → :48.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "hasReplayableFullSnapshot getReplayPlayerEvents normalize", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt structural playability validation + monotone timestamp repair before handing event streams to any player/renderer; adapt the FullSnapshot shape test to your recorder version.
