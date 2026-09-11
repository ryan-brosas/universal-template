<!-- capsule-v2 -->
# Typographic normalization — why does diff matching fail on smart quotes and how is it fixed in ONE place?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Where must smart quotes, unicode dashes, NBSP and HTML entities be normalized so model-provided text matches file content — and where is normalization explicitly NOT applied (raw output)?

## Option-map normalizer consumed by the similarity scorer; entity unescaper for display
**Path/Symbol:** `src/utils/text-normalization.ts` (`NORMALIZATION_MAPS.SMART_QUOTES` :6-8, `TYPOGRAPHIC` :13-14, `normalizeString` :48-77, `unescapeHtmlEntities` :85-99). Consumer: `src/core/diff/strategies/multi-search-replace.ts` `getSimilarity` :11-31.
**Signature:** `normalizeString(str: string, options?: NormalizeOptions): string` (defaults: smartQuotes+typographic+collapseWhitespace+trim all true); `unescapeHtmlEntities(text: string): string`.
**Data Shape:** Maps: U+201C/201D→`"`, U+2018/2019→`'`, U+2026→`...`, em/en dash→`-`, U+00A0→space. `&amp;` unescaped LAST (order preserves literal `&lt;` text).

### Decisive source
```ts
// multi-search-replace.ts getSimilarity — normalize BOTH sides before comparing:
const normalizedOriginal = normalizeString(original)
const normalizedSearch = normalizeString(search)
if (normalizedOriginal === normalizedSearch) return 1
// Levenshtein on the NORMALIZED pair ⇒ "should match content with smart quotes" passes
```
The maps are exported constants shared with CustomModesManager's YAML sanitizer conceptually, but each surface keeps its own table tuned to its parser. Normalization applies to COMPARISON only — the replacement text written into files keeps the diff's literal bytes apart from indent transplant.
**Flow:** model emits typographic characters (autocorrect, chat paste) → search chunk normalized → file slice normalized → similarity computed on the canonical forms → match found → ORIGINAL (un-normalized) replace content spliced in.
**Invariant:** Normalize-for-match but never normalize-for-output unless the host documents it; both sides must use the SAME options or scores skew; whitespace collapsing means line-level comparison treats runs of spaces as equal — acceptable for similarity, wrong for exact byte identity checks elsewhere.
**Probe:** `src/utils/__tests__/text-normalization.spec.ts` (map coverage); `multi-search-replace.spec.ts:901` "should match content with smart quotes", :881 extra-whitespace match, :922 empty-line non-exact-match negative.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "normalizeString NORMALIZATION_MAPS unescapeHtmlEntities", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the small option-map design and the compare-normalized/splice-original rule. Adapt map contents to your language's typography. Keep this utility dependency-free — it sits on the hot path of every fuzzy edit.
