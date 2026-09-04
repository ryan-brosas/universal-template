<!-- capsule-v2 -->
# Attachment blank/like + write ledger — how does an attachment cell define "blank", and how do attachment writes preserve server-side metadata across updates?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What do blank/notblank/like mean on a JSON-array attachment column, and what is the id-preservation contract in parseUserInput?

## AttachmentGeneralHandler
**Path/Symbol:** `packages/nocodb/src/db/field-handler/handlers/attachment/attachment.general.handler.ts` — filterBlank :15-34; filterNotblank :36-55; like/nlike empty-value duality :57-83; parseUserInput :85-189.
**Signature:** `filterLike(...): !args.val ? this.filterBlank(...) : super.filterLike(...)` — the sidebar's empty "contains" chip means BLANK for attachments (documented UX convention :53-54).
**Data Shape:** Storage: JSON array of `{id, url, path?, title?, mimetype?, size?...}`; tombstones: literal `'[]'` and `'null'` strings count as blank alongside NULL.

### Decisive source
```ts
// :20-27 — the three-way blank:
nestedQb.whereNull(sourceField)
  .orWhere(sourceField, '[]')
  .orWhere(sourceField, 'null');
// :124-131 — old-value authority: ids must exist in the OLD cell or they're rejected;
// present ids have the ENTIRE old row re-assigned over the patch:
if (attachment.id) {
  const oldAttachmentRow = oldValueMap.get(attachment.id);
  if (!oldAttachmentRow) throwError(`Attachment id ${attachment.id} not exists on old data`);
  Object.assign(attachment, oldAttachmentRow);   // server metadata wins
} else {
  if (!attachment.url) throwError('New attachment must include a url');
  attachment.id = 'temp_' + tempIndex++;
}
```

**Flow:** parseUserInput parses string/array → builds oldValueMap from oldData → validates each entry (existing id ⇒ merge old; no id ⇒ require url, mint temp_N) → `arrDetailedDiff` removed ids are deleted from FileReference (orphan GC at WRITE time) → validateNumberOfFilesInCell cap → output maps temp entries to `{id, url, status:'uploading'}` and persists only extractProps allowlist fields on settled ones.
**Invariant:** (1) `Object.assign(attachment, oldAttachmentRow)` is the security boundary — clients can never inject signed-url paths/sizes for known ids. (2) Removal triggers FileReference.delete DURING input parsing, before any column write succeeds; a failed subsequent write does not resurrect them (compensation belongs to the caller). (3) The `'null'` string arm exists because some writers serialize empty arrays as the literal string.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "not exists on old data" (:144); search_graph resolves `AttachmentGeneralHandler.parseUserInput Method` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "validateNumberOfFilesInCell", limit: 5 });
```

## Verdict
Adopt old-row-authority merge + write-time GC + three-shape blank; adapt the file-reference model; omit AttachmentOracleHandler (empty subclass at this pin). Caveat: no direct tests at pin.
