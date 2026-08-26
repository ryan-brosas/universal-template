<!-- capsule-v2 -->
# FTS5 search — natural-language normalization, operator passthrough, and LIKE fallback

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does a full-text search over memories and session messages turn a free-form user query into a robust FTS5 MATCH — preserving explicit operators, quoting natural-language terms, and falling back to LIKE for CJK/malformed input without ever returning a silent empty for a query that could match?

## FTS5 query normalization + search
**Path/Symbol:** `src/store/fts-query.ts` — `normalizeFts5Query` (32–43), `buildFallbackFts5Query` (50–64), `normalizeNaturalLanguageFts5Query` (76–81), `buildNaturalLanguageFallbackQuery` (87–95), `hasExplicitFts5Operator` (5–7), `isFts5QueryError` (97–101). `src/store/sqlite-memory-store.ts:searchMemories` (685–799). `src/store/session-search.ts:searchSessions` (91–225).
**Signature:** `normalizeFts5Query(query: string) → string`; `searchMemories(dbManager, query, {project?, target?, category?, limit?}) → SqliteMemoryEntry[]`; `searchSessions(dbManager, query, {limit?, project?, role?, since?}) → SessionSearchResult[]`.
**Data Shape:** FTS5 MATCH is done via a subquery `m.id IN (SELECT rowid FROM memory_fts WHERE memory_fts MATCH ?)` (and `m.rowid IN (SELECT rowid FROM message_fts WHERE message_fts MATCH ?)` for sessions), joined with scope filters, `ORDER BY last_referenced/timestamp DESC LIMIT ?`. Natural-language terms become individually quoted `"term"` joined by space (implicit AND); connector stopwords `and/or/not/near` are dropped in NL mode.

### Decisive source
```ts
// fts-query.ts
const FTS5_OPERATOR_PATTERN = /\b(OR|AND|NOT|NEAR)\b/;
export function hasExplicitFts5Operator(query) { return FTS5_OPERATOR_PATTERN.test(query.trim()); }

export function normalizeFts5Query(query) {
  const trimmed = query.trim(); if (!trimmed) return '';
  if (hasExplicitFts5Operator(trimmed)) return trimmed; // raw FTS5 syntax passes through
  return collectNaturalLanguageTerms(trimmed)
    .map((term) => `"${term.replace(/"/g, '""')}"`).join(' '); // implicit AND
}

export function buildFallbackFts5Query(query) {
  // multi-term NL → quoted terms joined by ' OR ' (broader)
  return terms.length > 1 ? terms.map(t => `"${t.replace(/"/g,'""')}"`).join(' OR ') : null;
}

export function isFts5QueryError(err) {
  const msg = err.message.toLowerCase();
  return msg.includes('fts5') || msg.includes('unterminated string');
}

// searchMemories (685-799): exact → on parse error, NL retry → NL fallback → generic OR fallback
const exactResults = runSearch(normalizedQuery);
if (exactResults.length > 0) return exactResults;
if (ftsParseError) { // uppercase operator words that failed to parse
  const nlQuery = normalizeNaturalLanguageFts5Query(query);
  ... return runSearch(nlQuery) || runSearch(buildNaturalLanguageFallbackQuery(query));
}
const fallbackQuery = buildFallbackFts5Query(query);
if (fallbackQuery && fallbackQuery !== normalizedQuery) return runSearch(fallbackQuery);
return exactResults;

// searchSessions (91-225): same recovery, then LIKE fallback for CJK substrings
// executeSearch({type:'like', terms}) → (m.content LIKE ? ESCAPE '\' OR ...) with %escaped%
```

**Flow:** (1) normalize the query: explicit uppercase operators pass through raw; otherwise quote each NL term for implicit AND. (2) Run the FTS5 MATCH subquery with scope filters. (3) If no results and the raw query failed to parse (uppercase operator words like "DO NOT USE FIND /"), retry as quoted natural language, then an OR fallback. (4) If still nothing, try the broader OR fallback. (5) For sessions, if FTS5 still misses (e.g. Chinese substrings), fall back to a `LIKE` search over terms with `%`/`_` escaped. A query that legitimately matches nothing keeps its exact semantics (no spurious broadening of valid operator queries).

**Invariant:** valid explicit operator queries are never broadened; a query that fails to parse is retried as natural language rather than silently returning empty; LIKE fallback escapes `%` and `_` so they match literally; all filters (project/target/category/role/since) and ordering/limit survive every fallback path.

**Probe:** `tests/store/sqlite-memory-store.test.ts` — `should match multi-word queries without requiring an exact phrase` (:348), `should ignore lowercase connector words in natural-language queries` (:354), `should fall back to broader natural-language matching when strict term matching misses` (:359), `should not broaden explicit operator queries` (:368), `should preserve explicit quoted phrase searches` (:374), `should recover natural-language queries with uppercase operator words and punctuation` (:380). `tests/store/session-search.test.ts` — `should find mixed Chinese/English queries via fallback` (:170), `should find Chinese-only substrings via LIKE fallback` (:181), `should escape LIKE wildcard characters during fallback` (:215). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "normalizeFts5Query searchMemories searchSessions buildFallbackFts5Query isFts5QueryError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the quoted-term implicit-AND normalization, the operator passthrough, the parse-error NL recovery, the OR fallback, and the LIKE fallback with escaping. Adapt the connector stopword set, the FTS5 table/column names, and the scope-filter columns to the host. Omit the session-role/since filters and the CJK-specific LIKE fallback unless a target needs them.
