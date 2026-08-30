<!-- capsule-v2 -->
# Streaming partial citations — how do citation cards appear while the JSON is still streaming?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How do you render structured citation objects incrementally from a token stream whose JSON block may be half-complete or never closed?

## String-aware brace scanner over complete objects only
**Path/Symbol:** `backend/src/lib/chat/citations.ts:232` (`parsePartialCitationObjects`). Direct test: `src/lib/__tests__/citations.test.ts` ("parsePartialCitationObjects" describe, 7 cases).
**Signature:** `parsePartialCitationObjects(text) -> ParsedCitation[]`.
**Data Shape:** scans from the FIRST `[` before `</CITATIONS>` (text after the close tag is cut first); returns normalized citations for every COMPLETE `{...}` object seen so far; incomplete tails and malformed middles are skipped.

### Decisive source
```ts
if (char === "\\") { escaped = inString; continue; }  // backslash only escapes INSIDE strings
if (char === '"') { inString = !inString; continue; }
if (inString) continue;                               // braces/brackets in quotes are data
if (char === "{") { if (depth === 0) objectStart = i; depth += 1; }
else if (char === "}") { ... depth -= 1;
    if (depth === 0 && objectStart >= 0) { try { parse slice } catch {} }
} else if (char === "]" && depth === 0) break;        // array close ends the scan
```

**Flow:** streaming layer accumulates deltas into `streamingCitationsBuffer`, re-parses per delta, and emits a `{type:"citations",status:"partial",citations}` snapshot whenever `partial.length > streamedCitationCount` — count-monotonic so snapshots are append-shaped and idempotent per new object.
**Invariant:** Escaped-quote handling (`escaped` flag set ONLY while in-string, cleared next char) keeps `"quote": "he said \"{ok}\""` intact; a `}` at depth 0 (outside any object) is ignored rather than corrupting state; scanning stops hard at `]`. Malformed complete objects are dropped individually without invalidating later ones.
**Probe:** `grep -c 'it(' src/lib/__tests__/citations.test.ts` → 29 total (7 in this describe): no-array-start → [], trailing incomplete ignored, braces+escaped quotes inside strings, post-close-tag content ignored, stops at `]`, malformed-then-valid.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "parsePartialCitationObjects streaming citations", limit: 10 });
```

## Verdict
Adopt the quote/escape-aware scanner + monotonic partial-snapshot emission as portable contracts; adapt snapshot event shape to your SSE vocabulary; omit doc/case kind specifics.
