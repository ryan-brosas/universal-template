<!-- capsule-v2 -->
# Session anchor search — bounded markdown-request JSONL search with scan caps and term scoring

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent search raw session JSONL files by a structured markdown request (from/to/cwd/all/any/exclude) — bounding the scan with file/line caps, scoring term matches, and merging adjacent hits into contiguous ranges — without ever scanning the whole corpus unbounded?

## Session anchor search
**Path/Symbol:** `src/store/session-anchor-search.ts` — `searchSessionAnchors` (72–122), `parseMarkdownRequest` (124–228), `parseDateTime` (230–247), `findJsonlFiles` (249–262), `searchJsonlFile` (264–336), `mergeAdjacentHits` (338–369), `sortRanges` (371–380), `scoreTerms` (382–392), `buildReason` (394–407), `containsAny` (409–412), `textualizeEvent` (437–441), `collectStrings` (455–468).
**Signature:** `searchSessionAnchors(markdown: string, {sessionsDir?, maxFiles?, maxLines?}) → { success, ranges: SessionAnchorRange[], message? }`.
**Data Shape:** `SessionAnchorRange = { path, startLine, endLine, sessionId?, cwd?, startTime?, endTime?, score?, reason }`. Request fields: `from`/`to` (date or ISO), `cwd`, `limit` (default 50, max 100), `all`/`any`/`exclude` (list sections with `- item` lines). Defaults: `maxFiles=5000`, `maxLines=500000`. Text is extracted from JSON events via `collectStrings` skipping metadata keys (`type`, `id`, `timestamp`, `cwd`, `role`, etc.).

### Decisive source
```ts
// parseMarkdownRequest (124-228): strict field validation
const fieldMatch = /^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$/.exec(trimmed);
// supported: from, to, cwd, limit (VALUE_FIELDS) and all, any, exclude (LIST_FIELDS)
// list items must be '- item' lines; duplicate fields rejected; limit capped at MAX_LIMIT (100)
// requires at least one constraint: from/to, cwd, all, or any

// searchJsonlFile (264-336): line-by-line scan with caps
for (let index = 0; index < lines.length; index += 1) {
  scannedLines += 1;
  if (scannedLines > maxLines) return { success:false, message: `... exceeding the configured scan cap of ${scanCap}...` };
  const event = JSON.parse(line); // invalid JSON → error with path:line
  const sessionId = getSessionId(event) ?? currentSessionId; // carry-forward
  const cwd = getCwd(event) ?? currentCwd;
  if (request.cwd && cwd !== request.cwd) continue;
  // time filter; then textualizeEvent + scoreTerms
  const termScore = scoreTerms(text, request);
  const matchesTerms = request.hasTextConstraint ? termScore > 0 : true;
  hits.push({ ..., score: request.hasTextConstraint ? termScore : 1, reason: buildReason(request, text) });
}

// mergeAdjacentHits (338-369): contiguous same-path, same-reason, consecutive-line hits merge
if (last && last.path === hit.path && last.endLine + 1 === hit.lineNumber && last.reason === hit.reason) {
  last.endLine = hit.lineNumber; last.score += hit.score; last.text += "\n" + hit.text; ...
}

// scoreTerms (382-392): all terms must all match (else 0); any terms boost score
const matchedAll = request.all.filter(t => lower.includes(t.toLocaleLowerCase()));
const matchedAny = request.any.filter(t => lower.includes(t.toLocaleLowerCase()));
if (request.all.length > 0 && matchedAll.length !== request.all.length) return 0;
if (request.any.length > 0 && matchedAny.length === 0) return 0;
return matchedAll.length * 2 + matchedAny.length;
```

**Flow:** (1) Parse the markdown request strictly, rejecting unknown/duplicate fields, invalid dates, and unconstrained requests. (2) Enforce the file cap (`maxFiles`) before scanning; reject requests that would scan too many files. (3) Recursively find `.jsonl` files, then scan each line under the line cap, carrying forward sessionId/cwd, applying cwd/time/term filters, and scoring term matches. (4) Merge adjacent hits into contiguous ranges, filter out ranges containing `exclude` terms, sort by score (text-constrained) or time, and limit. (5) Return ranges with a reason string.

**Invariant:** a request must be bounded (time, cwd, or text constraint) or it is rejected; the scan is capped by file count and line count so a broad request fails loudly instead of scanning the whole corpus; text matching is case-insensitive literal substring (all = AND, any = OR, exclude = suppress); adjacent same-reason hits merge into contiguous ranges.

**Probe:** `tests/store/session-anchor-search.test.ts` — `accepts a minimal time window and caps limit` (:39), `returns diagnostics for duplicate, unknown, empty, and unconstrained requests` (:56), `measures broadness with scan caps instead of rejecting request shape` (:67), `allows cwd-only requests as bounded source anchors` (:88), `does not match metadata fields as text` (:118), `returns contiguous timestamped ranges for time-window-only queries` (:130), `matches all and any terms as case-insensitive literal substrings` (:149), `removes ranges containing exclude terms` (:170), `fails on invalid JSON lines with path and line` (:200). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "searchSessionAnchors parseMarkdownRequest searchJsonlFile mergeAdjacentHits scoreTerms", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the strict markdown-request parsing, the file/line scan caps, the case-insensitive all/any/exclude term scoring, the adjacent-range merging, and the metadata-key exclusion in text extraction. Adapt the request field names, the caps, and the JSON event shape to the host. Omit the sessionId/cwd carry-forward and the time-window range building unless a target has the same JSONL session format.
