<!-- capsule-v2 -->
# Session context epoch — how do you make system context durable per session while letting it evolve without re-baselining history?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** The provider request carries a rendered system context (environment, instructions, MCP/skill state). It must be durable (survive restarts), it must gate which history rows are "already consumed", and it must be able to CHANGE mid-session without rewriting the message log. How is the baseline stored, advanced, and replaced?

## Epoch row: initialize / prepare / replace / advance
**Path/Symbol:** `packages/core/src/session/context-epoch.ts` (`initialize` :23-29, `prepare` :31-38, `prepareOnce` :40-78, `initializeOnce` :80-89, `reset` :111-119, `insert` :122-139, `replace` :141-159, `advance` :161-173); table `SessionContextEpochTable` in `sql.ts` (:168).
**Signature:** `initialize(db, context, sessionID) → Effect<{baseline, baselineSeq} | undefined, InitializationBlocked>`; `prepare(db, events, context, sessionID) → Effect<{baseline, baselineSeq}, InitializationBlocked | ContextSnapshotDecodeError>`.
**Data Shape:** row = `{session_id, baseline: string (rendered context), snapshot: Record<Key, SourceSnapshot>, baseline_seq: number}`; Prepared = `{baseline, baselineSeq}`.

### Decisive source
```ts
// context-epoch.ts:40-78 — prepare: reconcile normally, replace only after a compaction passed the baseline
const [value, stored, compaction] = yield* Effect.all(
  [context, find(db, sessionID), SessionHistory.latestCompaction(db, sessionID)], { concurrency: "unbounded" })
if (!stored) { const generation = yield* SystemContext.initialize(value); const baselineSeq = yield* insert(db, sessionID, generation); return {...} }
const snapshot = yield* Schema.decodeUnknownEffect(SystemContext.Snapshot)(stored.snapshot).pipe(
  Effect.mapError((error) => new ContextSnapshotDecodeError({ sessionID, details: String(error) })))
const replacementSeq = compaction !== undefined && compaction.seq > stored.baseline_seq ? compaction.seq : undefined
const result = replacementSeq ? yield* SystemContext.replace(value, snapshot) : yield* SystemContext.reconcile(value, snapshot)
if (result._tag === "Unchanged" || result._tag === "ReplacementBlocked") return { baseline: stored.baseline, baselineSeq: stored.baseline_seq }
if (result._tag === "ReplacementReady") {
  const baselineSeq = replacementSeq ?? (yield* EventV2.latestSequence(db, sessionID))
  yield* replace(db, sessionID, baselineSeq, result.generation); return { baseline: result.generation.baseline, baselineSeq }
}
yield* events.publish(SessionEvent.ContextUpdated,
  { sessionID, messageID: SessionMessage.ID.create(), timestamp: yield* DateTime.now, text: result.text },
  { commit: () => advance(db, sessionID, result.snapshot).pipe(Effect.orDie) })   // snapshot-only advance
return { baseline: stored.baseline, baselineSeq: stored.baseline_seq }
```

**Flow:** initialize runs first every turn: no row → build the generation (fails InitializationBlocked if ANY source is unavailable — and writes NO row, so the next turn retries cleanly) and insert at the current latest event sequence. Row exists → undefined, and prepare takes over. prepare decodes the stored snapshot (corruption → ContextSnapshotDecodeError, a typed failure that aborts the turn before any request is sent). If a compaction landed AFTER the baseline seq, the context is REPLACED (full re-render) and the epoch rebaselines at the compaction seq (or latest sequence when no compaction); otherwise it is RECONCILED against the per-source snapshot: Unchanged/ReplacementBlocked keep the stored baseline; Updated publishes a ContextUpdated event whose commit callback advances ONLY the snapshot column — the new context text reaches the model as a system message in history while baseline_seq stays put. reset deletes the row (session teardown/move).

**Invariant:** at most one epoch row per session; a blocked initialize leaves no row; below-baseline system content is consumed into the durable baseline and never re-sent as history; an Updated context becomes a visible system message, not a silent baseline swap; Replacement happens only when a compaction invalidated the old baseline window; decode failure fails the turn, never the store.
**Probe:** `packages/core/test/session-runner.test.ts` (:666-758): "retries the first provider turn after system context becomes available" pins blocked-initialize → InitializationBlocked failure, ZERO requests, pending steer retained, and the epoch table UNDEFINED (no row written); "fails gracefully when a stored context snapshot cannot be decoded" pins ContextSnapshotDecodeError with zero requests after corrupting the snapshot row; "reuses one durable baseline after the context producer changes" pins both requests carrying the OLD baseline in request.system, the new context arriving as a trailing system-role message, exactly ONE `session.next.context.updated.1` event, and replay-stable message count. Source pin:
```bash
grep -n 'replacementSeq' packages/core/src/session/context-epoch.ts   # expect 3
grep -n 'ContextUpdated' packages/core/src/session/context-epoch.ts   # expect 1
grep -n 'SessionContextEpoch.initialize\|SessionContextEpoch.prepare' packages/core/src/session/runner/llm.ts  # expect 2 (:183/:198)
```

## Runner wiring
**Path/Symbol:** `packages/core/src/session/runner/llm.ts` (`runTurnAttempt` :173-224).
**Signature:** per turn: `initialized ?? prepare` → `entriesForRunner(db, id, system.baselineSeq)` → `request.system = [agent.system, system.baseline].filter(non-empty)`.
**Data Shape:** the epoch's baselineSeq is the single input to history loading (see session-history-baseline-gating.md).

### Decisive source
```ts
// llm.ts:183-204 — initialize first, prepare fallback, then load history gated by the baseline
const initialized = yield* SessionContextEpoch.initialize(db, loadSystemContext(agent), session.id)
...
const system = initialized ?? (yield* SessionContextEpoch.prepare(db, events, loadSystemContext(agent), session.id))
...
const entries = yield* SessionHistory.entriesForRunner(db, session.id, system.baselineSeq)
...
system: [agent.info?.system, system.baseline].filter((part) => part !== undefined && part.length > 0).map(SystemPart.make),
```

**Flow:** the agent's own system prompt comes first, then the durable baseline; either may be absent. Because initialize returns undefined once a row exists, steady-state turns pay only prepare (one concurrent triple-read + one compare), and the baseline string is stable across turns until a ReplacementReady or reset.

**Invariant:** the request's system block is a pure function of (agent config, epoch row); history loading always uses the SAME baselineSeq that produced the baseline string, so consumed/visible partitioning can never drift between the two.
**Probe:** session-runner.test.ts "includes the effective default agent system before durable context" pins agent-system-first ordering; "rebuilds the baseline directly after completed compaction" pins request.system flipping from ["Initial context"] to ["Replacement context"] after Compaction.Ended + changed producer. Source pin:
```bash
grep -n 'entriesForRunner(db, session.id, system.baselineSeq)' packages/core/src/session/runner/llm.ts  # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SessionContextEpoch initialize prepare replace advance baseline_seq ContextUpdated SystemContext reconcile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-column epoch (rendered baseline + per-source snapshot) with three distinct transitions: insert-once (initialize), snapshot-only advance (Updated → visible system message), and full rebaseline (ReplacementReady, anchored at the compaction seq). Adopt "blocked initialize writes no row" — a partial write would poison every later turn. Adopt decode-failure-as-typed-turn-error: a corrupt snapshot must fail the turn before any provider request, never silently re-baseline. Adapt SystemContext's source-keyed snapshot to your context producers; omit the compaction-anchored replacement if you have no compaction (then replacementSeq is always undefined and only reconcile runs). Direct test sections read (session-runner.test.ts :666-758, :1039-1075, :1337-1370); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
