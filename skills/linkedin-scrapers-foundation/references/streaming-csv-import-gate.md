<!-- capsule-v2 -->
# Streaming CSV import with header checksum gate — how do I import user-supplied campaign CSVs into entities at scale, rejecting wrong/foreign files and partial rows WITHOUT loading the file or losing row-level error detail?

**Source:** lh-basis (Linked Helper extract) NO LICENSE — learn-only, patterns recorded, zero code copied `extract mtime 2026-08-15`; Codebase Memory project `lh-basis` (dist plane outside roots — direct source probes). **Question:** what is the correct streaming pipeline (parse → header contract → batched entity save) so a 100k-row CSV import is memory-bounded, rejects mismatched files loudly BEFORE any insert, and reports per-row failure reasons instead of a binary pass/fail?

## Papaparse step-stream transform → checksum + foreign-file header gate → batched Duplex saver

**Path/Symbol:** `CSVParser/ParseCSVTransform.js:ParseCSVTransform`; `CSVParser/SaveEntitiesFromBatchedRowsStream.js:SaveEntitiesFromBatchedRowsStream`; `CSVParser/campaigns.js:_loadCampaignsFromFile/_checkHeadersCheckSumLoadCampaignsFromFile/_getUnprocessedReason/_createCampaignByCSVRow`; `helpers/adjustments.js` sibling `FirstChunkMinSizeStream.js`.
**Signature:** `ParseCSVTransform(delimiter)` (Transform: bytes in, row objects out); `SaveEntitiesFromBatchedRowsStream(saveEntities, checkHeaders)` (Duplex); `_loadCampaignsFromFile(db, liAccount, deps, {file, delimiter}) -> [entities[], unprocessedRowsWithReason[]]`.
**Data Shape:** rows arrive as papaparse `{data: string[], errors[]}`; headers row = first chunk's `data[0]`; unprocessed record = `{row, reason: UnprocessedCSVCampaignReason}` where reason ∈ {MISSING_QUOTES, INVALID_CHECK_SUM, INVALID_ACTION_TYPE, INVALID_ACTION_SETTINGS, FAILED_TO_CREATE_CAMPAIGN}; campaign row = named columns + numbered action families (`action_type_1`, `action_cool_down_1`, `add_tags_successful_1`, …) + trailing `checksum` column.

### Decisive source
```js
// STREAMING PARSE with abort-on-bad-first-row (header row IS the schema probe):
parse(parserStream, {
  step: (row, parser) => {
    if (!this.isFirstRowParsed && row.errors.length) return parser.abort();
    this.isFirstRowParsed = true;
    if (!this.push(row)) { this.pausedParser = parser; parser.pause(); } // backpressure
  },
  complete: (res) => {
    if (res.meta.aborted) return this.emit("error", new Error("Can't parse headers"));
    this.push(null); …
  }
});
_transform(chunk, enc, cb) {                       // propagate backpressure to input
  this.parserStream.write(chunk, enc, cb)
    ? cb() : this.parserStream.once("drain", cb);
}

// HEADER CONTRACT: exact-order checksum + foreign-file detection, BEFORE any row:
_checkHeadersCheckSumLoadCampaignsFromFile(headers) {
  _checkHeadersCheckSum(headers);                                   // order-sensitive digest
  if (headers.includes("company_id")) throw new Error("couldn't upload organizations csv");
  if (headers.includes("public_id"))  throw new Error("couldn't upload people csv");
}

// PER-ROW CLASSIFY-NOT-THROW: each bad row becomes a REASONED record…
function _getUnprocessedReason(msg) {
  return msg?.includes("missing quotes")      ? Reason.MISSING_QUOTES
       : msg?.includes("invalid check sum")   ? Reason.INVALID_CHECK_SUM
       : msg?.includes("invalid action type") ? Reason.INVALID_ACTION_TYPE
       : /* … */ Reason.FAILED_TO_CREATE_CAMPAIGN; }

// BATCHED SAVE: strip header once, checkpoint by ROW INDEX for resume:
async _save(rows) {
  if (!this.isFirstChunkParsed && rows.length) {
    this.headersRow = rows[0].data;
    if (this.headersRow.length) this.checkHeaders(this.headersRow);  // gate HERE
    rows.splice(0, 1);
  }
  const saved = await this.saveEntities(this.headersRow, rows,
                                       this.lastProcessedRowIndex + 1);
  this.lastProcessedRowIndex += rows.length;                          // checkpoint
  this.isFirstChunkParsed = true; return saved;
}
```

**Flow:** file stream → ParseCSVTransform (papaparse in step mode; first-row errors abort the WHOLE import because a broken header means every later row would mis-save) → first chunk's header row goes to the checksum+foreign-file gate before anything persists → remaining rows flow through SaveEntitiesFromBatchedRowsStream which strips the header exactly once and hands bounded batches to `saveEntities(headers, batch, startRowIndex)` → per-row failures are caught INSIDE the row factory and returned as `{row, reason}` records while good rows still commit → caller receives `[entities, unprocessedWithReason]` for a partial-success report.
**Invariant:** the header gate must run on the FIRST CHUNK only and must run BEFORE the first entity insert — validating lazily per-row lets half a foreign file land. The checksum covers header ORDER (not just membership): reordering columns must invalidate the file, because the numbered `action_*_N` family is position-fragile. Backpressure is propagated on BOTH hops (`parser.pause()` when downstream won't accept, `.once("drain", cb)` toward upstream) or memory blows up on big files. Empty cell ⇒ explicit `null` (the row factory maps `""`→null) so "cleared field" survives round-trips as absent rather than empty-string. Row-index checkpoints make imports resumable: `lastProcessedRowIndex + 1` is passed INTO the saver so it can report progress against original file positions.
**Probe:** no public tests (proprietary extract) — coverage caveat. Deterministic probes verified at extract (anchored at `lh-basis/core/local-source/dist/CSVParser`; migration probe from `dist`): `grep -c "isFirstChunkParsed" SaveEntitiesFromBatchedRowsStream.js` ⇒ 3 (init-check inside `_save`, set after first batch, read nowhere else); `grep -c "company_id" campaigns.js` ⇒ 1 (single decisive foreign-file site); `grep -oP "CREATE TABLE IF NOT EXISTS \w+" migrations/169.js` pins the sibling migration idiom (`BEGIN IMMEDIATE` wrapper = same transactional discipline); graph anchor via semantic query "working intervals table migration" resolves numbered migrate functions in project `lh-basis-migrations`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis-migrations", semanticQuery: ["create working_intervals table day_and_night column"], limit: 10 });
```

## Verdict
Adopt the four contracts: first-chunk header gate (checksum over order + foreign-file markers), classify-not-throw per-row reasons enum, single-pass header stripping keyed by a first-batch latch, and row-index checkpoints for resumability. Adapt papaparse to your CSV engine but keep the abort-on-broken-header behavior; adapt the reason enum vocabulary to your domain. Contrast nocodb's json-import-streaming (peek/unshift bracket-wrap for JSON arrays — same streaming family, different delimiter problem) and ledger-contrast-csv-vs-summary (CSV as OUTPUT state; this capsule is CSV as INPUT). Omit nothing structural. Patterns only — no-license source.
