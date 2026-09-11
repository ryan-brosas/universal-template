<!-- capsule-v2 -->
# Session revert stage machine — how do you make session revert reversible (stage / cancel / commit) across two engine generations?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Reverting a coding session must undo file changes AND message history, but the user may change their mind before committing. How does opencode structure that as a three-phase machine — and how did the same seam evolve from imperative v1 to event-sourced v2?

## v2: event publishers + projector-side deletion
**Path/Symbol:** `packages/core/src/session/revert.ts` (`plan` :27-58, `stage` :60-96, `clear` :98-111, `commit` :113-121) + `packages/core/src/session.ts` (revert wiring :430-450) + `packages/server/src/handlers/session.ts` (revert.stage/clear/commit handlers :216-300, Snapshot.Error → UnknownError{ref} mapping :243/:272).
**Signature:** `stage({session, messageID, files?}) → Effect<Revert.State, MessageNotFoundError>`; `Revert.State = {messageID, snapshot?, diff?, files?}`; events `SessionEvent.RevertEvent.{Staged, Cleared, Committed}`.
**Data Shape:** Staged carries the full revert state; Cleared/Committed carry only sessionID (+messageID for commit). The projector writes `SessionTable.revert` on Staged, nulls it on Cleared, and deletes messages after the boundary on Committed.

### Decisive source
```ts
// core/session/revert.ts:36-55 — plan: first-wins per-file snapshot map over assistant messages AFTER the boundary
const rows = yield* db.select().from(SessionMessageTable)
  .where(and(eq(SessionMessageTable.session_id, input.sessionID),
             eq(SessionMessageTable.type, "assistant"),
             gt(SessionMessageTable.seq, boundary.seq)))
  .orderBy(asc(SessionMessageTable.seq)).all()...
for (const file of message.snapshot.files ?? [])
  if (!files.has(file)) files.set(file, Snapshot.ID.make(message.snapshot.start))

// core/session/revert.ts:67-94 — stage is a PUBLISHER; restore happens now, deletion happens in the projector
const original = input.session.revert?.snapshot ? ... : yield* snapshot.capture()
if (input.files !== false) for (const [file, tree] of next) restore.set(file, tree)
if (restore.size) yield* snapshot.restore({ files: restore })
yield* events.publish(SessionEvent.RevertEvent.Staged, { sessionID, timestamp, revert })
```

**Flow:** `plan` resolves the boundary message's seq and collects every assistant message after it whose snapshot has a start tree, building `Map<RelativePath, Snapshot.ID>` where the FIRST occurrence wins — the earliest assistant message's tree is the restore target per file. `stage`: original = existing staged snapshot ?? fresh capture; if re-staging, the original trees are restored first; the plan merges into the restore map unless `files === false`; `snapshot.restore({files})` applies it; diff original→new capture over the planned paths; publish Staged with `{messageID, snapshot, diff, files}`. `clear` restores the original trees and publishes Cleared. `commit` publishes Committed and does nothing else — the PROJECTOR deletes messages after the boundary (test pins: Staged → `SessionTable.revert` set, Cleared → null, Committed → only the boundary row remains in SessionMessageTable). Handler maps `Snapshot.Error` to 500 `UnknownError{ref: "err_<8hex>"}` with the cause logged under the ref.
**Invariant:** Stage is the only phase that touches the filesystem; commit never restores or diffs — it only announces, and convergence happens in the projector. A file's restore target is the EARLIEST post-boundary assistant tree (first-wins), so later edits cannot poison the undo target. Re-staging always restores the previous original before applying the new plan.
**Probe:** `packages/core/test/session-projector.test.ts:99-130` (pins Staged → revert row `{messageID, snapshot:"tree", files:[]}`, Cleared → `revert` null, Committed → message table reduced to `[boundary]`); source pin:
```bash
grep -n 'if (!files.has(file)) files.set(file' packages/core/src/session/revert.ts
grep -n 'RevertEvent.Staged\|RevertEvent.Cleared\|RevertEvent.Committed' packages/core/src/session/revert.ts
```
expect 1 + 3 hits.

## v1: imperative three-phase with lastUser boundary snap
**Path/Symbol:** `packages/opencode/src/session/revert.ts` (`revert` :38-90, `unrevert` :92-100, `cleanup` :102-125) — wired to the legacy busy-gated routes cited in session-http-handler-plane.md.
**Signature:** `revert({sessionID, messageID, partID?}) → Effect<Session.Info, BusyError>`; `unrevert({sessionID})`; `cleanup(session)`.
**Data Shape:** `Session.Info.revert = {messageID, partID?, snapshot?, diff?}` + summary `{additions, deletions, files}`; `session_diff/<sessionID>` Storage key holds the per-file diff list.

### Decisive source
```ts
// opencode/src/session/revert.ts:47-63 — boundary snaps to the last USER message when no partID given
for (const msg of all) {
  if (msg.info.role === "user") lastUser = msg.info
  ...
  if ((msg.info.id === input.messageID && !input.partID) || part.id === input.partID) {
    const partID = remaining.some((item) => ["text", "tool"].includes(item.type)) ? input.partID : undefined
    rev = { messageID: !partID && lastUser ? lastUser.id : msg.info.id, partID }
  }
}
// :70-72 — re-staging restores the previous original BEFORE reverting collected patches
rev.snapshot = session.revert?.snapshot ?? (yield* snap.track())
if (session.revert?.snapshot) yield* snap.restore(session.revert.snapshot)
yield* snap.revert(patches)
```

**Flow:** `revert` asserts not-busy, scans all messages tracking `lastUser`, finds the target message/part, and snaps the boundary to `lastUser.id` when no partID was given — the user message that triggered the reverted work survives, everything from it onward is in range. Patch parts at/after the boundary are collected; snapshot = existing ?? fresh track; re-staging restores the existing original first, then `snap.revert(patches)` applies them in reverse; diff vs snapshot; `session_diff` written to Storage with failures ignored; `Session.Event.Diff` published; `setRevert` stores state + summary. `unrevert` asserts not-busy, restores the snapshot, clears state. `cleanup` MATERIALIZES: removeMessage for every message after the boundary (or removePart from partID onward within the boundary message), then clearRevert.
**Invariant:** Both generations share the contract: stage/cancel are filesystem-only and repeatable; the destructive step (v1 cleanup / v2 projector commit) is separate and idempotent-by-absence (no revert state → no-op). v1 gates on the busy runner; v2 gates on event ordering instead.
**Probe:** `packages/opencode/test/session/revert-compact.test.ts:111-271` ("should properly handle compact command after revert" pins: revert sets `sessionInfo.revert.messageID`, messages still 4 while staged, cleanup removes userMsg2+assistantMsg2 and clears revert state); source pin:
```bash
grep -n 'rev.snapshot = session.revert?.snapshot' packages/opencode/src/session/revert.ts
grep -n 'lastUser ? lastUser.id : msg.info.id' packages/opencode/src/session/revert.ts
```
expect 1 + 1 hits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SessionRevert stage clear commit plan RevertEvent Staged Cleared Committed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-phase shape (stage = filesystem-only + repeatable, cancel = restore original, commit = announce-and-converge) for any destructive-but-reviewable operation; adopt first-wins per-file restore-target selection so later edits cannot poison the undo target; adopt the v2 split where the handler publishes and a projector converges, keeping the handler free of multi-step mutation. Adapt the v1 lastUser boundary snap (revert lands on the user turn, not the assistant turn) to your transcript model; omit the v1 patch-collection path if your snapshot engine tracks per-message trees like v2. Direct tests read whole (session-projector.test.ts 567L section, revert-compact.test.ts 683L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
