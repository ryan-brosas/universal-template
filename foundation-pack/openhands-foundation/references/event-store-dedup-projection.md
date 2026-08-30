<!-- capsule-v2 -->
# Event store dedup & projection — a global conversation-event store that survives replayed backlogs, token floods, and conversation switches

**Source:** OpenHands / All-Hands-AI MIT `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How should one global event store dedup reconnect replays, stay cheap under per-token commits, and swap conversations without half-applied state?

## Connected graph-selected seam
**Path/Symbol:** `src/stores/use-event-store.ts:useEventStore` (zustand `create`, 137–237) with helpers `appendEvent`/`applyAddEvent`/`sortEventState` (86–135).
**Signature:** `{ events: OHEvent[]; eventIds: Set<string|number>; uiEvents: OHEvent[]; loadedConversationId: string|null; addEvent(e); addEvents(es); clearEvents(); clearEventsForConversation(id|null) }`.
**Data Shape:** `OHEvent = OpenHandsEvent & { isFromPlanningAgent?: boolean }`. Two arrays are maintained in lockstep: raw `events` and render-projected `uiEvents` (actions folded with their observations, Think/Finish observations dropped via `handleEventForUI`).

### Decisive source
```ts
const eventId = getEventId(event);
// Transient deltas merge by position and are never persisted/resent, so skip
// id tracking for them — copying the growing `eventIds` Set per token would
// otherwise be O(n^2).
const isDelta = isStreamingDeltaEvent(event);
if (!isDelta && eventId !== undefined && state.eventIds.has(eventId)) return state; // O(1) dedup
…
if (!needsSorting(state.events, event) && !needsSorting(state.uiEvents, event)) return next;
return sortEventState(next); // full timestamp sort ONLY when out of order
```
Atomic switch (`clearEventsForConversation`): one `set` clears events/eventIds/uiEvents AND records the new `loadedConversationId`, "so no subscriber can observe a half-applied state"; the provider's layout effect compares `loadedConversationId` to tell a real switch from a remount of the same conversation.

**Flow:** WS/replay/REST-page events enter via `addEvent` or bulk `addEvents` → id-duplicate events update nothing (callers use the same check to skip non-idempotent side effects) → adjacent same-sender deltas fold into the last event by position → an out-of-order arrival triggers one full ISO-timestamp sort of both arrays → conversation switch clears atomically before the next history seed.

**Invariant:** `loadedConversationId` always names the conversation whose events are in the arrays (even after bare `clearEvents`); duplicate ids never append twice; delta floods never copy the id Set; array order is chronological whenever any observer can see it.

**Probe:** `__tests__/stores/use-event-store.test.ts` pins dedup/sort/clear behavior. RUNNER BLOCK: vitest not executable here; decisive ranges read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "event store dedupe eventIds sort timestamp conversation clear", limit: 8 });
// executed this pass -> sortEventState src/stores/use-event-store.ts 131-135,
// compareEventsByTimestamp 24-35, clearEventsForConversation 216-222 (has_more: true)
```

## Verdict
Adopt id-set dedup with transient-delta exclusion, sort-only-on-disorder, dual raw/projected arrays, and the atomic clear+rebind. Adapt the projection rules to your renderer's folding needs. Omit the dev-only `window.__OH_EVENT_STORE__` fixture hook. Coverage: `no_recorded_issue` on both cited paths.
