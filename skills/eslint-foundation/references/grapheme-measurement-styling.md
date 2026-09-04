<!-- capsule-v2 -->
# Grapheme-aware text measurement — how do you count "characters" for length limits and table alignment when emoji and ANSI codes are in play?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do id-length/key-spacing measure names, and how does the stylish formatter align columns containing color codes?

## getGraphemeCount + upperCaseFirst
**Path/Symbol:** `lib/shared/string-utils.js:getGraphemeCount(value)` (:39–52) + `upperCaseFirst(string)` (:27–33).
**Signature:** `getGraphemeCount(value): number` — fast path `ASCII_REGEX` (`/^[\u0000-\u007f]*$/u`) returns `.length`; otherwise lazy `Intl.Segmenter("en-US")` singleton counts segments.
**Data Shape:** module-level `let segmenter; segmenter ??= new Intl.Segmenter(...)` — constructed once per process, only when first non-ASCII string appears.

### Decisive source
```js
if (ASCII_REGEX.test(value)) return value.length;
segmenter ??= new Intl.Segmenter("en-US");
let graphemeCount = 0;
for (const unused of segmenter.segment(value)) graphemeCount++;
```

**Flow:** ASCII short-circuit (the overwhelmingly common case) → user-perceived-character counting via ICU.
**Invariant:** the unit is GRAPHEME, not UTF-16 code unit: `"👨‍👩‍👦"` is 1 despite 8 code units, and `"葛󠄀"` is 1 despite 2 code points — rules enforcing name-length limits must use this or they reject legitimate identifiers. The ASCII fast path is exact for ASCII (length ≡ graphemes) so no behavioral divergence. Locale is pinned ("en-US should be supported everywhere") to avoid environment-dependent counts.
**Probe:** `tests/lib/shared/string-utils.js` (:39–61 upperCaseFirst edge cases incl. empty/1-char; :62–90 grapheme table incl. ZWJ families, skin-tone modifiers, VS16 sequences); `tests/lib/rules/id-length.js:284/:886` (`var 葛󠄀 = 2` counted as 1).

## ANSI-safe column alignment (consumer)
**Path/Symbol:** `lib/cli-engine/formatters/stylish.js:stringLength(str)` (:91 `util.stripVTControlCharacters(str).length`) feeding `lib/shared/text-table.js` (:35–68 width reduce + pad).
**Flow:** formatter measures messages with escape codes STRIPPED so colored cells don't widen columns, then re-colors; line:column pairs are dimmed via post-table regex on digits.
**Invariant:** alignment math and coloring must be separable — measuring decorated strings shifts every subsequent row. text-table pads by computed max width per column with right/left alignment flags.
**Probe:** `tests/lib/cli-engine/formatters/stylish.js` (:37–126 FORCE_COLOR matrix asserting stripped vs styled output equality).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "getGraphemeCount upperCaseFirst text-table stylish", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.shared.string_utils.getGraphemeCount" });
```

## Verdict
Adopt the ASCII-fast-path + lazy Segmenter singleton verbatim; adopt strip-then-measure-then-decorate ordering for any colored tabular output; omit upperCaseFirst if your locale handles casing.
