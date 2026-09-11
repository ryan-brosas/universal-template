<!-- capsule-v2 -->
# Aggregate versioned event-sourcing kernel — how do I give campaign/account entities an audit-safe event history with snapshot hydration, without letting stale writes or unknown events corrupt state?

**Source:** lh-basis (Linked Helper extract) NO LICENSE — learn-only, patterns recorded, zero code copied `extract mtime 2026-08-15`; Codebase Memory project `lh-basis-migrations` (kernel plane outside indexed roots — direct source probes). **Question:** what is the minimal correct event-sourcing contract (aggregate base, per-type migration gate, SQL stores) for a domain where every flag change must be replayable and concurrency-safe?

## BaseAggregate apply/persist split → strict-version hydration → typed-id + TimePoint primitives

**Path/Symbol:** `contexts/kernel/domain/aggregates/BaseAggregate.js:BaseAggregate` (whole class); `contexts/kernel/domain/eventing/DomainEvent.js:DomainEvent.create` (+`DomainEventId.generate`); `contexts/kernel/domain/primitives/TimePoint.js:TimePoint.from/isAfter`; `contexts/kernel/domain/primitives/TypedId.js:TypedId.equals/validate`; `contexts/campaign/domain/aggregates/Campaign.js:Campaign.changeReadonlyFlag/_assertCampaignIsEditable/hydrate`; `contexts/li-account/domain/events/SSI/migrations/migrateEvents.js:migrateSSIEvent`; `contexts/kernel/application/errors/{ConcurrencyError,UnsupportedEventMigrationError}.js`.
**Signature:** `apply(event)` / `applyPersisted(event)` / `applyPersistedAll(events)` / `pullPendingEvents() -> Event[]`; static `hydrate(id, events, snapshot?) -> Aggregate`; handler map `getEventHandlers(): {<EventType>: fn}`; store `SQLEventsStore.persistEvents(aggregateId, events, fromVersion)` stamps `{...e, aggregateVersion: fromVersion + i + 1}`.
**Data Shape:** event = `{id: DomainEventId, aggregateId, type, data, metadata:{eventVersion}, occurredAt: TimePoint}`; persisted rows additionally carry `aggregateVersion` (1-based monotonic); snapshot = frozen domain state + `version`, stored via `SQLSnapshotStore.persistSnapshot(aggregateId, data, version)`.

### Decisive source
```js
// NEW events: bump version optimistically, park in pendingEvents, apply NOW.
apply(e) {
  const v = this.version + 1;
  this.pendingEvents.push({...e, aggregateVersion: v});
  this.version = v;
  this.handleEvent(e);
}
// PERSISTED events: the recorded version IS truth — any gap throws. This is
// what makes a torn write or lost event impossible to load silently:
applyPersisted(e) {
  if (e.aggregateVersion !== this.version + 1)
    throw new Error(`Invalid event version sequence. Expected ${this.version+1}, got ${e.aggregateVersion}`);
  this.version = e.aggregateVersion;
  this.handleEvent(e);
}
handleEvent(e) {
  const h = this.getEventHandlers()[e.type];
  if (!h) throw new Error(`No handler for event: ${e.type}`);  // unknown = loud
  h(e);
}
// Migration gate at the persistence edge: only known versions pass; future or
// legacy-but-unmigrated versions FAIL LOUD instead of hydrating wrong shape:
function migrateSSIEvent(raw, version) {
  switch (raw.type) {
    case "SSIScoreCollected":
      if (version === 1) return raw;
      throw new UnsupportedEventMigrationError(version, raw.type); … }
}
// Guard-before-apply inside the aggregate (guard lives in the method, not UI):
changePausedFlag(value) {
  this._assertCampaignIsEditable();          // readonly → CampaignReadonlyError
  this._assertCampaignIsVisible();           // hidden   → CampaignHiddenError
  if (this._isPaused !== value) this.apply({type:"PausedFlagChanged", …});
}
```

**Flow:** command → guard asserts current projected state (visible/editable) → no-op if value unchanged → `DomainEvent.create` mints id + TimePoint + per-event `eventVersion` → `apply` bumps `aggregateVersion`, queues pending, runs handler synchronously → repository persists via `SQLEventsStore.persistEvents` (transactional batch stamping consecutive versions) and snapshots via `SQLSnapshotStore` → reload = fetch last snapshot (`findLastSnapshotByAggregateId`) + events since its version → `hydrate` replays through the SAME handlers after each event clears the migration gate.
**Invariant:** new events are versioned by the AGGREGATE while persisted events are validated AGAINST it — the two paths must never be merged into one "set version" helper or gaps stop being detected. Handlers are the ONLY place state mutates (command methods mutate nothing directly), so a snapshot's frozen state plus a suffix of events always reproduces the exact state; `getSnapshot()` must return `Object.freeze`d data so callers can't fork history. Unknown event types throw at BOTH edges (handler lookup and migration switch) — silent skipping is what turns old databases into corrupted aggregates. Identity comparison goes through `TypedId.toString()` equality with a `validate` that throws on foreign-shaped ids; time comparisons go through `TimePoint.isAfter/isBefore` on `.getTime()` so wall-clock subclasses can't leak in. The `AccountSSIHistory.ensureNew` pattern extends this to user-level ordering: reject any event whose occurredAt precedes the last accepted one.
**Probe:** no public tests (proprietary extract) — coverage caveat. Deterministic probes verified at extract: `grep -c "Invalid event version sequence" BaseAggregate.js` ⇒ 1 (the strict-hydration guard exists exactly once; run from `lh-basis/core/local-source/dist/contexts/kernel/domain/aggregates/`); migration twins pin schema: `lh-basis-migrations` semantic query "create working_intervals table day_and_night column" resolves numbered `migrate(db)` Functions (42/44/169 top hits); `grep -l "working_intervals_adjustments" $REFERENCE_ROOT/linkedin/lh-basis/core/local-source/dist/migrations/*.js` ⇒ exactly `169.js` creating the UNIQUE-keyed adjustments table; `UnsupportedEventMigrationError` referenced by every `migrateEvents.js` (SSI + campaign + people-action + organization-action).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis-migrations", query: "CREATE TABLE", limit: 10 });
```

## Verdict
Adopt the dual-path versioning discipline (optimistic for new, strict-gap-check for persisted), guard-before-apply inside aggregate methods, freeze-on-snapshot, loud unknown-event handling, and per-event-type version gates throwing `UnsupportedEventMigrationError` until a real migration is written. Adapt storage to your DB and swap the hand-rolled bus for your framework's — but keep hydration flowing through the same handler map as live application. Omit the inversify token ceremony if you don't use DI. Contrast nocodb's audit-id-migration (append-only ledgers WITHOUT replay): choose event sourcing only when you need state reconstruction, not just audit trails. Patterns only — no-license source.
