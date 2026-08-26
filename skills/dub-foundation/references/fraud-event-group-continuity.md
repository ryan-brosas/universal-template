<!-- capsule-v2 -->
# Fraud event group continuity choreography — how do events fold into ONE pending group per (program, partner, type), and which reads decide dedup vs new-group?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** When a second fraud event arrives for a partner that already has a pending group, why must it join the EXISTING group instead of opening another — and what exact query sequence guarantees that?

## Five-step funnel: hash-dedup → pending-group reuse → createMany → counter increment
**Path/Symbol:** `apps/web/lib/api/fraud/create-fraud-events.ts:createFraudEvents` (:17-178).
**Signature:** `async function createFraudEvents(fraudEvents: CreateFraudEventInput[]): Promise<{ affectedGroups: Pick<FraudEventGroup,"partnerId"|"programId"|"type">[] }>`.
**Data Shape:** group identity key = `createGroupCompositeKey` = `` `${programId}:${partnerId}:${type}` `` (:129-133); ids minted `frg_` (groups) / `fre_` (events) via `createId`; return value = affected groups (pending + just-created) consumed by hold callers.

### Decisive source
```ts
// 1. in-memory hash dedupe
const uniqueEvents = Array.from(new Map(eventsWithHash.map((e) => [e.hash, e])).values());
// 2. DB dedupe: same hash while its group is STILL PENDING = duplicate
const existingEvents = await prisma.fraudEvent.findMany({
  where: { hash: { in: ... }, fraudEventGroup: { status: "pending" } } });
// 3. reuse pending groups for continuity; only missing combos open new groups
const existingGroups = await prisma.fraudEventGroup.findMany({
  where: { OR: newEvents.map((e) => ({ programId, partnerId, type, status: "pending" })) } });
// 4. batch inserts
await prisma.fraudEventGroup.createMany({ data: newGroups });   // frg_ ids
const createdEvents = await prisma.fraudEvent.createMany({ data: newEventsWithGroup }); // fre_ ids
// 5. counters via allSettled (never fails the caller)
await Promise.allSettled(finalGroups.map((group) => prisma.fraudEventGroup.update({
  where: { id: group.id },
  data: { lastEventAt: new Date(),
          eventCount: { increment: <count of this group's new events> } } })));
```
(create-fraud-events.ts :30-168 condensed)

**Flow:** empty-input early return → hash+dedupe against pending-group members → drop duplicates → find pending groups for the remaining combos → create ONLY the missing ones → map each event to its group id through the composite-key lookup (`finalGroupLookup.get(...)!`) with `partnerId` overridden by `getPartnerIdForFraudEvent` (duplicate-account events are attributed to the DUPLICATE partner's id :135-146) → insert → bump `lastEventAt`/`eventCount` on every touched group.
**Invariant:** (1) at most ONE pending group per `(programId, partnerId, type)` — resolved/expired history never blocks a fresh group, so re-offending partners get NEW cases after resolution; (2) dedup is status-QUALIFIED: an identical event under a RESOLVED group still creates a new row in a new group; (3) `lastEventAt` is the expiry clock — every append refreshes it, so active fraud rings keep their groups alive (expiry cron keys off it); (4) group-counter updates ride allSettled so a counter hiccup can't orphan created events.
**Probe:** anchored at dub repo root: `grep -c 'status: "pending"' apps/web/lib/api/fraud/create-fraud-events.ts` = **2** (both qualifying queries); `grep -o 'createGroupCompositeKey' apps/web/lib/api/fraud/create-fraud-events.ts | wc -l` = **3**; `grep -c 'frg_' apps/web/lib/api/fraud/create-fraud-events.ts` = **1**; `grep -c 'increment' apps/web/lib/api/fraud/create-fraud-events.ts` = **1**; `grep -c 'Promise.allSettled' apps/web/lib/api/fraud/create-fraud-events.ts` = **1**. Direct tests: `apps/web/tests/fraud/fraud-groups.test.ts` pins the READ side of groups (list/filter-by-status/type/partner/groupId, schema parse) over HTTP.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createFraudEvents", limit: 5 });
```

## Verdict
Adopt the composite-key group continuity model and the pending-status-qualified dedup. Adapt id prefixes and counter mechanics. Omit performance.now() instrumentation logging.
