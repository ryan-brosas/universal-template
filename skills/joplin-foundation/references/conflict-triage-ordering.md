<!-- capsule-v2 -->
# Conflict triage — when is a clash worth preserving, and in what order must the copies be written?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How does the sync engine turn each conflict class into local state without losing either side?

## handleConflictAction
**Path/Symbol:** `packages/lib/services/synchronizer/utils/handleConflictAction.ts` :13-135; eligibility `packages/lib/models/Note.ts` :1093-1105 (`mustHandleConflict`); consumer `packages/lib/Synchronizer.ts` :865-874.
**Signature:** `handleConflictAction(action, ItemClass, remoteExists, remoteContent, local, syncTargetId, itemIsReadOnly, dispatch)`.
**Data Shape:** `conflictActions = [NoteConflict, ResourceConflict, ItemConflict]` (from `./types`).

### Decisive source
```ts
// NoteConflict: does the conflict even matter?
let mustHandleConflict = true;
if (!itemIsReadOnly && remoteContent) {
    mustHandleConflict = Note.mustHandleConflict(local, remoteContent);
}
if (mustHandleConflict) {
    const conflictNote = await Note.createConflictNote(local, ItemChange.SOURCE_SYNC);
    createdConflictNoteId = conflictNote.id;
    const base = await Note.syncBaseContent(syncTargetId, local.id);   // read BEFORE rebuild
    await ConflictNoteState.save({ note_id: conflictNote.id, base_body..., remote_... });
}
...
// For note/resource conflicts: overwrite local with remote (or delete if remote gone)
if (remoteExists) {
    local = remoteContent;
    await ItemClass.save(local, { autoTimestamp: false, changeSource: ItemChange.SOURCE_SYNC, nextQueries: syncTimeQueries });
    ...
    // Link after the save above, which rebuilds the sync_items row.
    if (createdConflictNoteId) {
        await Note.setBaseConflictNoteId(syncTargetId, local.id, createdConflictNoteId);
    }
}
```

**Flow:** ItemConflict (non-notes) = last-synced-wins: local silently becomes remote content; if remote vanished, local deleted WITHOUT children for folders (`deleteChildren: false` guards against cascade data loss). NoteConflict: reload latest local → relevance gate → create conflict-note copy of the user's version into Conflicts folder → record {base, remote} snapshot for later 3-way merge UI → THEN overwrite original with remote → link conflict note LAST. ResourceConflict: conflict-resource note + reset fetch_status IDLE so the winning blob re-downloads.
**Invariants:** (1) relevance gate: only title/body/encryption differences matter — todo_completed-style drift takes remote silently (encrypted notes ALWAYS conflict since content can't be compared); (2) ORDER IS LOAD-BEARING: `setBaseConflictNoteId` runs only AFTER the remote-overwrite save because that save REBUILDS the sync_items row and would wipe an earlier link (in-source comment + dedicated test 'note conflict is created' asserting reload-before-create semantics, `handleConflictAction.test.ts`:14-44); (3) base snapshot must be captured BEFORE the same rebuild too (:68-70 comment); (4) editor-reload dispatch keeps mobile viewers honest after silent overwrites.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "await Note.setBaseConflictNoteId(syncTargetId, local.id, createdConflictNoteId);" packages/lib/services/synchronizer/utils/handleConflictAction.ts && grep -cF "localNote.body !== remoteNote.body" packages/lib/models/Note.ts && grep -n "Link after the save above" packages/lib/services/synchronizer/utils/handleConflictAction.ts'` (anchored at repo root; expects 1 / 1 / a line ≥117). Direct tests: `handleConflictAction.test.ts` (note conflict created / not created on equal content / dispatch emitted).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "handleConflictAction mustHandleConflict createConflictNote ConflictNoteState setBaseConflictNoteId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: three-class triage, relevance gate, copy-then-overwrite ordering with post-save linking, folder-delete child guard. Adapt: conflict storage to your model. Omit: ConflictNoteState UI merging.
