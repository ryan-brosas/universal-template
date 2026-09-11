<!-- capsule-v2 -->
# Airtable link-row spill — how do you buffer link cells for a whole base with flat memory?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Where do link cells wait between record creation and link fill, and what makes the buffer safe under size limits and crash cleanup?

## JSONL parts in deployment blob storage
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-link-spill.ts`:`AirtableLinkRowSpill` (:36–110).
**Signature:** `append(airtableTableId: string, rows: ISpilledLinkRow[]): Promise<void>`; `async *read(airtableTableId: string): AsyncGenerator<ISpilledLinkRow>`; `cleanup(): Promise<void>`.
**Data Shape:** `ISpilledLinkRow = { teableRecordId, cells: [{ airtableFieldId, ids[] }] }`; rows serialize one JSON object per line; per-table pending buffer flushes at `partMaxBytes = 4 MiB` into `{dir}/{tableId}.part-{seq5}.jsonl`; total staging capped by `TEABLE_IMPORT_SPILL_MAX_BYTES` (default 2 GiB).

### Decisive source
```ts
if (this.bytesWritten > this.maxBytes) {
  throw new Error(
    `The import link buffer exceeded ${this.maxBytes} bytes of staging storage; ` +
      'raise TEABLE_IMPORT_SPILL_MAX_BYTES to import this base'
  );
}
...
/** Streams the table's rows back, part by part, line by line. */
async *read(airtableTableId: string): AsyncGenerator<ISpilledLinkRow> {
  await this.flushPart(airtableTableId);   // tail part joins the read set
  for (const partPath of this.parts.get(airtableTableId) ?? []) {
    const stream = await this.storage.download(partPath);
    const lines = createInterface({ input: stream, crlfDelay: Infinity });
```

**Flow:** importer backs the spill with the deployment StorageAdapter (local/S3/MinIO) — same staging pattern as the .tea import, no container-local temp files → append buffers lines and uploads 4 MiB parts → fill phase reads rows streamed part-by-part → `cleanup()` clears maps and deletes the UUID dir prefix ONLY if anything was uploaded (`uploadedAnything` guard); the caller wraps the whole records phase in try/finally around cleanup.
**Invariant:** Memory stays flat regardless of base size — the ONLY data held for the whole run is old→new id maps of link-target tables. Read must flush the pending tail first or the last <4MiB of rows silently vanish. The budget error names its env knob so an operator can raise it without reading code.
**Probe:** `grep -cF "TEABLE_IMPORT_SPILL_MAX_BYTES" apps/nestjs-backend/src/features/airtable-import/airtable-link-spill.ts` returns 2. Direct tests: `airtable-link-spill.spec.ts` it('fails with a clear error past the staging budget') :31 and it('streams appended rows back per table in order and cleans up') :39.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"AirtableLinkRowSpill flushPart ISpillStorage","limit":5,"detail":"ids"}'
```

## Verdict
Adopt blob-backed JSONL spill parts with tail-flush-before-read and fail-loud budgeting for any two-phase id-remap pipeline; adapt part sizes/storage adapter; omit teable's UploadType bucket choice. Coverage caveat: none.
