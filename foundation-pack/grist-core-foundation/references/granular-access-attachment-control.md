<!-- capsule-v2 -->
# Granular access attachment control — how are attachment ids gathered, ownership-timed, and re-sent on a need-to-know basis so hidden cells can't leak blobs?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** When a user lacks full read access, how does the engine prevent attachment metadata from leaking, and how does the uploader's ownership window work?

## Need-to-know attachment filtering + ownership TTLs
**Path/Symbol:** `app/server/lib/GranularAccess.ts` — `needAttachmentControl` (:1206-1208), `_filterOutgoingAttachments` (:2634-2660), `_gatherAttachmentChanges` (:2662-2684), `assertAttachmentAccess` (:540-549), `isAttachmentUploadedByUser` (:551-558), `findAttachmentCellForUser` (:560-574); ownership constants `UPLOADED_ATTACHMENT_OWNERSHIP_PERIOD` (:142-144) and `HISTORICAL_ATTACHMENT_OWNERSHIP_PERIOD` (:146-148); `_attachmentUploads` MapWithTTL (:321).
**Signature:** `needAttachmentControl(docSession): Promise<boolean>` = `!await this.canScanData(docSession)`; `_filterOutgoingAttachments(cursors): Promise<ActionCursor[]>`.
**Data Shape:** `_attachmentUploads = MapWithTTL<number, string>(UPLOADED_ATTACHMENT_OWNERSHIP_PERIOD)` maps attachment id → uploader's SessionID. `HISTORICAL_ATTACHMENT_OWNERSHIP_PERIOD = 24h`.

### Decisive source
```ts
// _filterOutgoingAttachments — drop create/update actions on _grist_Attachments,
// then re-send the metadata for ids actually referenced by broadcast actions.
const attIds = new Set<number>();
for (const cursor of cursors) {
  const changes = await this._gatherAttachmentChanges(cursor);
  for (const attId of changes) { attIds.add(attId); }
  const { action } = cursor;
  if (!isDataAction(action) || isSomeRemoveRecordAction(action) || getTableId(action) !== "_grist_Attachments") {
    result.push(cursor);
  }
}
if (attIds.size > 0) {
  const act = this._docData.getMetaTable("_grist_Attachments").getBulkAddRecord([...attIds]);
  result.unshift({ action: act, docSession, actionIdx: cursors[0].actionIdx });
}
```
```ts
// _gatherAttachmentChanges — skip when the user is undoing their own recent history
if (options?.fromOwnHistory && options.oldestSource &&
  Date.now() - options.oldestSource < HISTORICAL_ATTACHMENT_OWNERSHIP_PERIOD) { return empty; }
```

**Flow:** when a user can't scan the whole doc (`needAttachmentControl` true), the engine strips all `_grist_Attachments` create/update actions from the outgoing broadcast and instead re-sends a `BulkAddRecord` for exactly the attachment ids referenced by the actions the user CAN see. The uploader gets a free window (`UPLOADED_ATTACHMENT_OWNERSHIP_PERIOD`, half the unused-attachment deletion delay) during which they can add/re-add their own uploads without access-control fuss, tracked by SessionID in `_attachmentUploads`. Undoing one's own actions within 24h skips the gathering entirely. `assertAttachmentAccess` verifies a specific cell actually contains an attachment before serving it; `findAttachmentCellForUser` walks the referencing cells to find one the user can see.
**Invariant:** attachment METADATA is only sent for attachments the user can actually reach through a visible cell — otherwise a hidden cell's blob URL would leak. The ownership window is keyed on SessionID, not user id, so the same user on a different session doesn't inherit it. `_gatherAttachmentChanges` only fires when the action touches an attachment column (`step.attachmentColumns`), so unrelated updates don't trigger the re-send.
**Probe:** `test/server/lib/GranularAccess.ts` — attachment control is exercised by the "respects owner-private tables" (:780) and attachment suites; `assertAttachmentAccess`/`findAttachmentCellForUser` are pinned by the attachment-access tests.
**Coverage caveat:** the ownership-TTL timing and the fromOwnHistory skip have no dedicated unit test (timing-dependent); source-verified.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "GranularAccess needAttachmentControl filterOutgoingAttachments gatherAttachmentChanges assertAttachmentAccess", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the need-to-know attachment re-send (strip create/update, re-emit referenced ids) plus the SessionID-keyed ownership window for any ACL engine over blob-referencing cells; adapt the TTLs; omit the fromOwnHistory undo skip if your undo is not per-user.
