<!-- capsule-v2 -->
# Multiline entry metadata regex — the `s` flag that keeps `decodeEntry` from mis-parsing multiline facts

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** Entry text may itself contain newlines — why does one regex flag decide whether multiline entries decode at all?

## decodeEntry metadata comment pattern
**Path/Symbol:** `src/store/memory-store.ts:decodeEntry` (:618–633; regex at :621); sibling copies of the same pattern: `src/store/sqlite-memory-store.ts:parseMetadataComment` (:197). Consumers: `memoryFullError` decoded envelope (`memory-full-error-entries.md`), `validateWholeEntryReplacement` line extraction (`whole-entry-replacement-guard.md`), failure rendering.
**Signature:** `/^(.*?)\s*<!--\s*created=([^,]+),\s*last=([^,>]+)(?:,\s*project64=([A-Za-z0-9_-]+))?\s*-->\s*$/s`.
**Data Shape:** raw entry = `<text> <!-- created=YYYY-MM-DD, last=YYYY-MM-DD[, project64=<b64url>] -->`; decode returns `{ text, created, lastReferenced, project }`; no-match ⇒ whole raw as text + today fallbacks (legacy entries without metadata).

### Decisive source
```ts
const match = raw.match(
  /^(.*?)\s*<!--\s*created=([^,]+),\s*last=([^,>]+)(?:,\s*project64=([A-Za-z0-9_-]+))?\s*-->\s*$/s
);   //                                                        the trailing /s ^^^
```

**Flow:** every read path splits the §-file into raw entry strings → decode strips the trailing metadata comment → without the `s` (dotAll) flag, `.*?` cannot cross a newline, so a MULTILINE fact followed by its metadata comment failed to match and the metadata leaked into the visible text (feeding #178's leak assertions).
**Invariant:** dotAll is required by the lazy-anywhere-text group; the anchor still forces the comment at the very END, so only genuine trailing comments strip. `[^,]+`/`[^,>]+` field scans stay single-line-safe because dates/base64 never contain commas. Both copies of this regex must change together — they encode one contract in two modules.
**Probe:** `npx tsx --test tests/store/memory-store.test.ts` — "strips metadata from multiline entries and accepts a full replacement" (:636, 3-line user entry round-trips with `/created=.*last=/` still on disk), plus the #178 leak assertions inside "includes current entries in memoryFullError response under reject strategy" (:369, no `<!--`/`created=` in decoded output for multiline content). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "decodeEntry parseMetadataComment project64", limit: 5 })`

## Verdict
Adopt the exact pattern WITH the `s` flag when porting the entry format; when adapting to your own metadata scheme, keep end-anchored stripping and test it against multiline payloads specifically. Pair with `memory-store.md`.
