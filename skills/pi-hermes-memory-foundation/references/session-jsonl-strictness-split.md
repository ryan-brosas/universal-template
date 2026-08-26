<!-- capsule-v2 -->
# Anchor-search JSONL strictness divergence — loud-fail scan vs skip-malformed parser

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** Two components read the same session JSONL corpus — when must a reader FAIL on a malformed line and when must it SKIP, and what does each choice buy?

## JSONL strictness split
**Path/Symbol:** `src/store/session-anchor-search.ts` — `searchJsonlFile` fail arm :291–296 (`try { event = JSON.parse(line) } catch { return { success:false, message: \`Invalid JSON in ${filePath}:${index + 1}\` } }`), carry-forward :298–302 (`sessionId = getSessionId(event) ?? currentSessionId`, same for cwd); vs `src/store/session-parser.ts` — `parseSessionFile` skip arm :110–116 (`try { entry = JSON.parse(line) } catch { continue; // Skip malformed lines }`). Direct tests: `tests/store/session-anchor-search.test.ts:200–212` (`fails on invalid JSON lines with path and line`); `tests/store/session-parser.test.ts` (skip behavior).
**Signature:** `searchJsonlFile(filePath, request, maxLines, scannedBefore, scanCap): { success:true; ranges; scannedLines } | { success:false; message }`.
**Data Shape:** anchor-search returns per-line diagnostics embedding `path:line`; the parser returns a whole-file `ParsedSession | null`.

### Decisive source
```ts
// session-anchor-search.ts (:291-296) — INDEXED RETRIEVAL READER: loud failure
let event: unknown;
try {
  event = JSON.parse(line);
} catch {
  return { success: false, message: `Invalid JSON in ${filePath}:${index + 1}` };
}
// ...and the WHOLE SEARCH aborts (searchSessionAnchors :106-108):
if (!fileResult.success) return { success: false, ranges: [], message: fileResult.message };

// session-parser.ts (:110-116) — INGESTION/INDEXING READER: resilience
try {
  entry = JSON.parse(line);
} catch {
  continue; // Skip malformed lines
}
```

**Flow:** (1) The anchor search serves an agent's interactive "where in my history did X happen" query over raw files it does not own — one corrupt line makes line-number→byte-position claims untrustworthy for everything after it, so it aborts the ENTIRE search naming the exact `path:line`. (2) The session parser builds the persistent SQLite index at ingestion time — a corrupt line there would poison one message at most, and failing the whole file would lose every good message in it to a single bad append, so it skips forward. (3) Both readers share the SAME event-shape tolerance upstream of parsing: sessionId/cwd/timestamp are extracted through four-shape accessors (`event.sessionId | event.session_id | event.type==="session" ? event.id | event.session.id`) and CARRIED FORWARD across events that omit them — sessions declare identity once, later events inherit.

**Invariant:** strictness follows WRITE-OWNERSHIP AND CONSUMER TRUST, not politeness: a reader whose output cites positions (ranges with startLine/endLine) must guarantee those positions are real, so it fails loudly and names the offending `path:line`; a reader whose output is derived content (indexed messages) maximizes yield per file and treats malformed lines as noise. Neither reader repairs or re-synchronizes partial lines — there is no "resync to next valid JSON" mode anywhere. The abort is total (no partial results returned alongside the error), keeping the success/error contract clean for callers that branch on `success`.

**Probe:** `tests/store/session-anchor-search.test.ts` — `fails on invalid JSON lines with path and line` (:200); contrast `tests/store/session-parser.test.ts` malformed-line cases (grep `malformed`). Coverage caveat: `tests/` is excluded from the graph index by design; probes are source-grounded from on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "scoreTerms collectStrings METADATA_TEXT_KEYS exclude", limit: 5 });
// live-verified rank-exact ×2: scoreTerms :382-392, collectStrings :455-468 (same module family)
```

## Verdict
Adopt the ownership/trust rule for any multi-reader JSONL store: position-citing readers fail loud with path:line, derived-content readers skip-and-count. Adapt the identity-carry-forward to your event schema. Omit nothing if you have both reader classes — this divergence IS the reusable contract.
