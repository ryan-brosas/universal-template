<!-- capsule-v2 -->
# Session history baseline gating — how do you load provider-facing history that excludes already-consumed system context and respects compaction windows?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** The message table holds user/assistant/system/compaction rows in one aggregate-ordered log. The provider request must NOT re-send system context that is already baked into the durable baseline, MUST still send system context that changed after the baseline (even if it predates a compaction), and must drop pre-compaction content in favor of the compaction summary. One SQL predicate does all three.

## The messageRows predicate
**Path/Symbol:** `packages/core/src/session/history.ts` (`latestCompaction` :13-22, `messageRows` :24-61, `load` :66-80, `loadForRunner` :82-88, `entriesForRunner` :90-99) + `packages/core/src/session/store.ts` (Interface :14-25, `runnerContext` :42-44).
**Signature:** `messageRows(db, sessionID, compaction?: {seq}, baselineSeq?) → Effect<rows[]>`; `entriesForRunner(db, sessionID, baselineSeq) → Effect<{seq, message}[]>`; `SessionStore.runnerContext(sessionID, baselineSeq) → Effect<Message[], MessageDecodeError>`.
**Data Shape:** rows ordered by seq ASC; entries carry the row seq alongside the decoded message (seq feeds promotion cutoffs and projector work); decode failure → MessageDecodeError{sessionID, messageID}.

### Decisive source
```ts
// history.ts:24-47 — one predicate: compaction window AND baseline consumption
const rows = yield* db.select().from(SessionMessageTable).where(
  and(
    eq(SessionMessageTable.session_id, sessionID),
    compaction
      ? or(
          gte(SessionMessageTable.seq, compaction.seq),
          baselineSeq === undefined ? undefined
            : and(eq(SessionMessageTable.type, "system"), gt(SessionMessageTable.seq, baselineSeq)),
        )
      : undefined,
    baselineSeq === undefined ? undefined
      : or(ne(SessionMessageTable.type, "system"), gt(SessionMessageTable.seq, baselineSeq)),
  ),
).orderBy(asc(SessionMessageTable.seq)).all().pipe(Effect.orDie)
```

**Flow:** read plainly, the predicate keeps a row iff: (1) it belongs to the session; (2) if a compaction exists — its seq is at-or-after the compaction, OR it is a system row above the baseline (the ContextUpdated messages survive the compaction window because they represent CURRENT context state, not summarized content); (3) if a baselineSeq is given — it is not a system row at-or-below the baseline (those are consumed into the durable baseline string and re-sending them would duplicate the system block). load() (public context) resolves baselineSeq from the epoch row itself (undefined when no epoch yet); entriesForRunner takes the runner's explicit baselineSeq so the SAME value that produced request.system also partitions history. latestCompaction picks the newest type="compaction" row by seq DESC.

**Invariant:** below-baseline system rows never reach the provider; above-baseline system rows ALWAYS reach the provider, even before the compaction point; with no compaction the log is complete except consumed system rows; with no epoch the log is fully complete; ordering is always seq ASC; a corrupt row fails the whole load with a typed error naming both IDs.
**Probe:** `packages/core/test/session-runner.test.ts`: "reuses one durable baseline after the context producer changes" pins the above-baseline system row appearing as the trailing system-role message while request.system keeps the old baseline; "preserves effective System updates while compaction rebaseline is blocked" pins BOTH halves at once — after Compaction.Ended + blocked rebaseline, request.system stays ["Initial context"] (old baseline, replacement blocked) yet the loaded history still contains "Changed context" as a system text (the carve-out); "rebuilds the baseline directly after completed compaction" pins the post-replacement world where the new baseline replaces the system block. `packages/core/test/session-history.test.ts` (read whole, 165L) pins the PUBLIC event-history pagination around the same log: exclusive `after` aggregate seq, gap-skipping without duplicates, exact-limit exhaustion reporting, migrated-session empty page, NotFoundError for missing sessions. Source pin:
```bash
grep -n 'gte(SessionMessageTable.seq, compaction.seq)' packages/core/src/session/history.ts  # expect 1
grep -n 'or(ne(SessionMessageTable.type, "system"), gt(SessionMessageTable.seq, baselineSeq))' packages/core/src/session/history.ts  # expect 1
grep -n 'loadForRunner' packages/core/src/session/history.ts  # expect 1 (:82; store.ts:43 is the facade call)
```

## Store facade
**Path/Symbol:** `packages/core/src/session/store.ts` (layer :27-58).
**Signature:** `get(sessionID) → Info|undefined`; `context(sessionID) → Message[]`; `runnerContext(sessionID, baselineSeq) → Message[]`; `message(messageID) → {sessionID, message}|undefined`.
**Data Shape:** thin Effect facade over drizzle; every query `.pipe(Effect.orDie)`s the driver layer; message() decodes `{...row.data, id, type}` through SessionMessage.Message.

### Decisive source
```ts
// store.ts:42-44 — runnerContext is the only load path that takes an explicit baseline
runnerContext: Effect.fn("SessionStore.runnerContext")(function* (sessionID, baselineSeq) {
  return yield* SessionHistory.loadForRunner(db, sessionID, baselineSeq)
}),
```

**Flow:** the runner uses entriesForRunner directly (it needs seqs); other consumers use store.context (epoch-derived baseline) or store.message for single-message lookup. The split keeps "who decides the baseline" explicit: the runner passes the one from prepare(), public readers derive it from the stored row.

**Invariant:** there is exactly one baseline source per load path and it is visible at the call site; the store never invents a baseline.
**Probe:** session-runner.test.ts "streams one request with registry definitions from chronological V2 user history" pins chronological loading of two resume:false prompts into one request (roles [user, user]); "automatically compacts into a completed summary and retained recent turn" pins post-compaction context = ["compaction", "assistant"] via store.context. Source pin:
```bash
grep -n 'readonly runnerContext' packages/core/src/session/store.ts  # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SessionHistory messageRows entriesForRunner loadForRunner latestCompaction baselineSeq SessionStore runnerContext", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-predicate partitioning: express "consumed system content", "current system updates", and "compaction window" as ONE where-clause over (type, seq, baselineSeq, compaction.seq) instead of post-filtering in memory — the database does the partitioning on every load. Adopt the system-row carve-out across the compaction boundary: anything that represents current state (not summarized content) must survive compaction. Adopt explicit-baseline-at-the-call-site for the execution path and stored-row-derived baseline for read paths, so the two can never drift. Adapt the row types to your event vocabulary; omit the carve-out if your system context never changes mid-session. Direct test sections read (session-runner.test.ts :666-758/:1039-1075/:1337-1370, session-history.test.ts 165L whole); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
