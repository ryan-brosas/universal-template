<!-- capsule-v2 -->
# Regex decomposition to AND trigrams / OR groups — when must prefiltering be abandoned entirely?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How does a trigram index accelerate regex search without ever missing matches?

## Soundness-first regex prefilter compiler
**Path/Symbol:** `src/index.zig` (`RegexQuery` :2801–2813, `decomposeRegex` :2819–2935, `extractLiteralTrigrams` :2938–3046, consumers `candidatesRegex` heap/mmap :1635/:2455).
**Signature:** `pub fn decomposeRegex(pattern: []const u8, allocator) !RegexQuery` where `RegexQuery = { and_trigrams: []Trigram, or_groups: [][]Trigram }`.
**Data Shape:** Literal runs ≥ 3 chars yield AND trigrams (dedup via seen-set); top-level alternations yield one merged OR group; empty `and_trigrams` + empty `or_groups` means UNFILTERABLE.

### Decisive source
```zig
// Soundness (#628): if ANY branch yields no trigrams (too short, or built
// from regex metachars like `.`/`.*`), that branch can match a line that
// contains none of the other branches' trigrams ... When that happens we
// cannot prefilter at all, so fall back to an unconstrained query
// (candidatesRegex returns null -> scan everything).
var any_branch_empty = false;
... if (branch_tris.len == 0) any_branch_empty = true; ...
if (any_branch_empty) { return RegexQuery{ .and_trigrams = &.{}, .or_groups = &.{} }; }
```
Chain-breakers inside literal runs: `.`, `\s\S\w\W\d\D\b\B`, `[...]`, anchors `^$`, parens, and any quantifier `*+?{` (which POPS the last literal first — `ab.` contributes only "ab"-run trigrams, `{n,m}` braces are consumed whole).

**Flow:** find top-level `|` outside brackets/groups (escape-aware depth scan) → alternation path: extract each branch's trigrams, merge into ONE OR group unless ANY branch was trigram-empty (then abandon) → non-alternation path: walk the pattern flushing literal runs into deduped trigram chains → `candidatesRegex`: intersect AND lists (hash-set minus removals) then union/subtract OR groups.
**Invariant:** NEVER let the prefilter be authoritative: an empty result from a filterable-looking alternation was the `a|b` "returns 0 and looks authoritative" bug (#628). A missing trigram posting list ⇒ zero candidates (sound because the trigram cannot exist anywhere); a NULL RegexQuery ⇒ full scan.
**Probe:** `src/test_index.zig` "decomposeRegex:" suite (:backslash-w breaks chain, character class breaks chain, dot breaks chain, pure literal extracts trigrams, escaped literal preserved, quantifier consumption incl. `{n}`,`{n,}`,`{n,m}`) + adversarial "{n,m} quantifier does not pollute trigram extraction".
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "decomposeRegex", limit: 10 });
```

## Verdict
Adopt decompose-to-trigrams with the abandon-on-unfilterable rule (it is the difference between a fast regex search and one that silently drops results); adapt metachar vocabulary to your engine; omit the nanoregex internals (verification layer, separate concern).
