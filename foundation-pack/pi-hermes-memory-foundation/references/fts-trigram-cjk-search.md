<!-- capsule-v2 -->
# Short-CJK literal fallback — trigram FTS cannot match ≤2-char CJK queries; route them to a scoped LIKE search

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** The trigram tokenizer fixed CJK substring matching — but a trigram index by definition needs ≥3 characters. What happens to one- and two-character CJK queries like 设备?

## isShortCjkLiteralQuery / runShortCjkFallback
**Path/Symbol:** `src/store/sqlite-memory-store.ts` — `isShortCjkLiteralQuery` (:194–198), `runShortCjkFallback` (:777–817), dispatch inside `searchMemories` :824–826 (after the exact FTS attempt returns nothing). Session-search twin: `src/store/session-search.ts:collectLikeTerms` (:211–212/:223–224) already routed CJK misses through LIKE.
**Signature:** `isShortCjkLiteralQuery(query: string): boolean` — `[...trimmed].length <= 2 && /^[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}]+$/u`; fallback runs `content LIKE '%q%' ESCAPE '\'` with `escapeLikePattern`.
**Data Shape:** fallback preserves EVERY scope filter as SQL conjuncts — `m.project IS NULL`/`= ?` when project given, `m.target = ?`, `m.category = ?` — ordered `last_referenced DESC LIMIT ?`.

### Decisive source
```ts
// FTS5's trigram tokenizer cannot match one- and two-character CJK terms.
// Use a scoped literal fallback only for those terms so FTS operators and
// normal tokenized searches retain their existing semantics.
const runShortCjkFallback = (): SqliteMemoryEntry[] => {
  const conditions: string[] = ["m.content LIKE ? ESCAPE '\\'"];
  const params: unknown[] = [`%${escapeLikePattern(query.trim())}%`];
  if (project !== undefined) { … m.project IS NULL / m.project = ? … }
  if (target)    { conditions.push('m.target = ?');   params.push(target); }
  if (category)  { conditions.push('m.category = ?'); params.push(category); }
  return db.prepare(`SELECT ${MEMORY_SELECT_COLUMNS} FROM memories m
    WHERE ${conditions.join(' AND ')} ORDER BY m.last_referenced DESC LIMIT ?`)
    .all(...params, limit).map(mapRow);
};
```

**Flow:** exact normalized FTS MATCH first → zero hits AND the query is ≤2 chars of pure CJK script → bypass the NL/OR fallback ladder entirely and return the literal scoped LIKE result. Longer or mixed-script queries keep the standard ladder (quoted-term AND → parse-error NL retry → OR fallback → session-side `collectLikeTerms` LIKE).
**Invariant:** the trigger is SCRIPT+LENGTH gated so explicit FTS5 operator syntax and ordinary tokenized searches never silently degrade to substring semantics; `%`/`_` in the query stay literal via escape; filters/order/limit survive the fallback unchanged. This is the query-time complement to the storage-time trigram migration (`fts-trigram-migration.md`) — migrate the index for ≥3-char matching, special-case the sub-trigram residue.
**Probe:** `npx tsx --test tests/store/sqlite-memory-store.test.ts` — "falls back to a scoped literal search for one- and two-character CJK queries" (:365), "finds pure CJK substrings with the trigram tokenizer" (:347, the ≥3-char positive control proving the migration handles long forms). `npx tsx --test tests/store/session-search.test.ts` — "finds pure CJK substrings with the trigram tokenizer" (:53). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "isShortCjkLiteralQuery runShortCjkFallback escapeLikePattern", limit: 5 })`

## Verdict
Adopt length-and-script-gated literal fallbacks around tokenized indexes whose minimum n-gram exceeds common query lengths. Adapt the script set and n-gram floor to your tokenizer. Pair with `fts5-search.md` (the general fallback ladder this short-circuits) and `fts-trigram-migration.md`.
