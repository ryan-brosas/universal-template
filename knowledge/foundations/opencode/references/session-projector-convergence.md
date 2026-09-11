<!-- capsule-v2 -->
# Session projector convergence — how do you converge an event stream into relational tables with a correct usage ledger, duplicate-creator detection, and revert truncation that also cuts the input ledger?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** The v2 engine publishes every session mutation as a durable event (pass-8 capsule covers admission). What does the CONVERGENCE side guarantee: that replaying the stream into SessionTable/MessageTable/PartTable/SessionInputTable keeps cost/token columns exactly right, treats a second creator event under one ID as corruption, and makes revert commit truncate BOTH the message history and the pending input ledger at the same boundary?

## Event registration table + duplicate-creator die
**Path/Symbol:** `packages/core/src/session/projector.ts` (layer :210-453, `SessionAlreadyProjected` :23, Created :214-231, MessageUpdated :259-272, PartUpdated :310-328, RevertEvent.Committed :413-450).
**Signature:** one `events.project(EventType, fn)` registration per event kind inside a Layer.effectDiscard; node = makeGlobalNode("session-projector", deps [EventV2.node, Database.node]).
**Data Shape:** SessionTable row from sessionRow(info) (full column mapping incl. cost/tokens/revert/permission); MessageTable/PartTable rows = {id, session_id, type, seq, time_created, data}; usage() extracts {cost, tokens} from step-finish parts only.

### Decisive source
```ts
// projector.ts:214-224 — a duplicate creator event is a DEFECT, not a skip
yield* events.project(SessionV1.Event.Created, (event) =>
  Effect.gen(function* () {
    const stored = yield* db.insert(SessionTable).values(sessionRow(event.data.info))
      .onConflictDoNothing().returning({ sessionID: SessionTable.id }).get().pipe(Effect.orDie)
    if (!stored) return yield* Effect.die(new SessionAlreadyProjected())
    ...
// projector.ts:310-327 — usage ledger: subtract previous, add next, possibly across sessions
yield* events.project(SessionV1.Event.PartUpdated, (event) =>
  Effect.gen(function* () {
    const row = yield* db.select().from(PartTable).where(eq(PartTable.id, id)).get().pipe(Effect.orDie)
    yield* db.insert(PartTable).values({ id, message_id, session_id, time_created, data })
      .onConflictDoUpdate({ target: PartTable.id, set: { data } }).run().pipe(Effect.orDie)
    const previous = row && usage(row.data)
    const next = usage(event.data.part)
    if (previous) yield* applyUsage(db, row.session_id, previous, -1)
    if (next) yield* applyUsage(db, sessionID, next)
  }),
)
// projector.ts:413-449 — revert commit truncates BOTH tables at the boundary seq
const boundary = yield* db.select({ seq: SessionMessageTable.seq }).from(SessionMessageTable)
  .where(and(eq(SessionMessageTable.session_id, event.data.sessionID), eq(SessionMessageTable.id, event.data.messageID)))
  .get().pipe(Effect.orDie)
if (!boundary) return yield* Effect.die(`Revert boundary message not found: ${event.data.messageID}`)
yield* db.delete(SessionMessageTable)
  .where(and(eq(SessionMessageTable.session_id, event.data.sessionID), gt(SessionMessageTable.seq, boundary.seq))).run().pipe(Effect.orDie)
yield* db.delete(SessionInputTable)
  .where(and(eq(SessionInputTable.session_id, event.data.sessionID),
    or(gt(SessionInputTable.admitted_seq, boundary.seq), gt(SessionInputTable.promoted_seq, boundary.seq)))).run().pipe(Effect.orDie)
yield* db.update(SessionTable).set({ revert: null, time_updated: ... }).where(...).run().pipe(Effect.orDie)
```

**Flow:** One project() registration per event kind. Created inserts the session row onConflictDoNothing; a missing returning row means a second creator event arrived under an existing ID → die(SessionAlreadyProjected) (replay of a different creator is a corrupt stream, not a benign duplicate). Updated/Moved/Deleted maintain the session row (Created with a workspaceID also stamps workspace time_used). MessageUpdated upserts by id; PartUpdated upserts by id and maintains the usage ledger: only step-finish parts carry cost/tokens (usage() extractor), updates subtract the PREVIOUS row's usage from ITS session and add the new usage to the EVENT's session (a part moving sessions moves its usage too); MessageRemoved/PartRemoved subtract before deleting. RevertEvent.Staged/Cleared set/clear the session.revert column; Committed resolves the boundary message's seq (die if missing), deletes message rows with seq > boundary, deletes input-ledger rows with admitted_seq OR promoted_seq > boundary, then clears revert. PromptAdmitted/Prompted delegate to SessionInput.projectAdmitted/projectPrompted (pass-8 capsule). Message projection goes through a SessionMessageUpdater adapter whose getCurrentAssistant picks the HIGHEST-seq assistant row and only if incomplete — "a newer turn supersedes stale incomplete rows; never resume an older assistant projection".

**Invariant:** Duplicate creator events under one ID are defects (die), never silent skips; session usage columns equal the sum of live step-finish parts (every update/removal applies ±usage symmetrically, across sessions when a part moves); revert commit truncates messages and the input ledger at the same aggregate-seq boundary; only the newest incomplete assistant projection is ever resumed.
**Probe:** `packages/core/test/session-projector.test.ts`: "projects staged, cleared, and committed reverts" (:81, pins Staged→revert set, Cleared→null, Committed→only the boundary row remains), "rejects distinct creator events that reuse one projected message ID" (:373), "updates only the newest incomplete assistant projection" (:439), "does not revive a stale incomplete assistant projection" (:497), "marks an inbox row promoted with the Prompted event sequence" (:202). Source pin:
```bash
grep -n 'applyUsage' packages/core/src/session/projector.ts                    # expect 5
grep -n 'SessionAlreadyProjected' packages/core/src/session/projector.ts       # expect 2
grep -n 'gt(SessionMessageTable.seq, boundary.seq)' packages/core/src/session/projector.ts  # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SessionProjector applyUsage SessionAlreadyProjected RevertEvent.Committed boundary getCurrentAssistant", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt duplicate-creator-as-defect for any event-sourced table with natural keys — onConflictDoNothing plus a returning-row check turns benign replays into loud stream-corruption signals instead of silent data loss. Adopt ±sign usage arithmetic applied to the PREVIOUS row's session for removals/moves, not just the event's session — ledger columns stay correct under part migration. Adopt dual-table boundary truncation (messages + input ledger at the same aggregate seq) for any revert feature that has a pending-work ledger. Adopt newest-incomplete-only supersession for resumable projections. Adapt the drizzle SQL to your ORM; omit the workspace time_used stamp if you have no workspace concept. Direct tests read (session-projector.test.ts sections :81-131, :202-245, :373-500); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
