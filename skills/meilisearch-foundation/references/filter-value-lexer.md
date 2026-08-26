<!-- capsule-v2 -->
# Filter value lexer — which characters delimit bare words, and how are quotes and escapes resolved?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** What is the exact character class of an unquoted value, and what is the two-layer escape story a porter must not flatten?

## parse_value / quoted_by / word_not_keyword
**Path/Symbol:** `crates/filter-parser/src/value.rs` (`parse_value` :146-251, `quoted_by` :22-61, `word_not_keyword` :64-77, `is_value_component` :253-255, `is_keyword` :261-279, geo-misuse guards :156-186).
**Signature:** `pub fn parse_value<'a, T: From<Span<'a>> + TokenLike>(input: Span<'a>) -> IResult<'a, T>`.
**Data Shape:** Bare word class = `c.is_alphanumeric() || ['_','-','.'].contains(&c)`; reserved keywords (AND/OR/IN/NOT/TO/EXISTS/IS/NULL/EMPTY/CONTAINS/STARTS/WITH/_geoRadius/_geoBoundingBox) are rejected as BARE words but legal quoted.

### Decisive source
```rust
// value.rs:42-51 — quoted_by: escape-aware scan; trailing lone backslash = MalformedValue
} else if c == '\\' {
    if let Some((_, c)) = i.next() {
        escaped |= c == quote;
    } else {
        return Err(nom::Err::Error(Error::new_from_kind(
            input.into(), ErrorKind::MalformedValue)));
    }
}

// value.rs:197-204 — the alt + mandatory trailing multispace0
let (input, value): (_, T) = terminated(
    alt((
        delimited(char('\''), cut(|input| quoted_by('\'', input)), cut(char('\''))),
        delimited(char('"'),  cut(|input| quoted_by('"', input)),  cut(char('"'))),
        word_not_keyword,
    )),
    multispace0,
)(input)
```

**Flow:** Strip leading whitespace; probe the RESERVED geo expressions FIRST (`_geoPoint`/`_geoDistance`/`_geo` always Failure ⇒ ReservedGeo; `_geoRadius`/`_geoBoundingBox` as VALUES ⇒ Misused* — better errors than "expected value"); then alt of single-quoted / double-quoted / bare-word. `quoted_by` hand-scans for the closing quote honoring `\x` pairs (only escapes OF THE QUOTE mark trigger unescape), then a SECOND unescape layer (`unescaper::unescape`) resolves numeric/hex escapes and rewrites the token's `modified_fragment`. Unmatched opening quote converts Char error ⇒ `MissingClosingDelimiter`.
**Invariant:** (1) The two layers differ: layer-1 only unescapes `\'`/`\"` sequences, layer-2 handles `\n`, `\x20`, unicode escapes — merging them changes accepted inputs; (2) keywords stay usable as QUOTED values (`"OR" EXISTS` parses); (3) empty quoted strings ARE valid values.
**Probe:** `crates/filter-parser/src/value.rs` tests `test_span` (:288-326), `test_escape_inside_double_quote` (:328-351), `test_value` (:375-441), `diagnostic` (:443-468). GREEN at pin (`cargo test -p filter-parser --lib` executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "parse_value word_not_keyword quoted_by unescape", limit: 10 });
```

## Verdict
Adopt the word character class, keyword-as-quoted-values rule, two-layer escaping, and geo misuse guards; adapt the Span/TokenLike plumbing; omit nom if host has its own combinator library — but keep the scan semantics byte-for-byte.
