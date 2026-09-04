<!-- capsule-v2 -->
# Filter grammar precedence ladder — why is OR[AND[...], x] the shape for `a AND b OR c`?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How does the nom grammar encode operator precedence, depth limits, and NOT-cancellation without an AST rewriter?

## parse_filter / parse_or / parse_and / parse_not
**Path/Symbol:** `crates/filter-parser/src/lib.rs` (`parse_primary` :883-923, `parse_expression` :926-928, `parse_filter` :931-933, `parse_or` :629-649, `parse_and` :652-672, `parse_not` :677-694) — BNF header comment :1-23; `MAX_FILTER_DEPTH: usize = 150` (:80).
**Signature:** `pub fn parse(input: &str) -> Result<Option<Self>, Error>` (None on blank input); internal `fn parse_or(input: Span, depth: usize) -> IResult<FilterCondition>`.
**Data Shape:** Output tree uses flat `Or(Vec)/And(Vec)` lists (Display renders `OR[..]`/`AND[..]`); every combinator thread carries a `depth` counter checked against 150 BEFORE descending.

### Decisive source
```rust
// lib.rs:629-648 — lowest binds last: or() calls and() calls not() calls primary()
fn parse_or(input: Span, depth: usize) -> IResult<FilterCondition> {
    if depth > MAX_FILTER_DEPTH { return Err(...ErrorKind::DepthLimitReached); }
    let (input, first_filter) = parse_and(input, depth + 1)?;
    // if we found a `OR` then we MUST find something next
    let (input, mut ors) =
        many0(preceded(ws(word_exact("OR")), cut(|input| parse_and(input, depth + 1))))(input)?;
    let filter = if ors.is_empty() { first_filter }
                 else { ors.insert(0, first_filter); FilterCondition::Or(ors) };
```
```rust
// lib.rs:684-691 — double-NOT cancellation at parse time
map(preceded(ws(word_exact("NOT")), cut(|input| parse_not(input, depth + 1))),
    |e| match e {
        FilterCondition::Not(e) => *e,                       // NOT NOT e == e
        _ => FilterCondition::Not(Box::new(e)),
    }),
```

**Flow:** `parse` rejects whitespace-only input as None; `parse_filter = terminated(parse_expression(depth 0), eof)`; expression ⇒ or ⇒ and ⇒ not ⇒ primary (parens recurse via `delimited(ws('('), cut(parse_expression(depth+1)), cut_with_err(')'))`). The `cut` after each keyword makes a found operator REQUIRE its right operand (Failure not recoverable Error). Depth is threaded through ALL levels — parens, NOT chains, and `_foreign(...)` bodies included. Test suite pins `channel = ponce AND 'dog race' != '...' OR subscribers > 1000` ⇒ `OR[AND[a,b], c]`, four consecutive NOTs collapsing to identity, and a 2 MiB all-OR filter now PARSING (depth guard only fires on nesting, not length).
**Invariant:** (1) Precedence is structural: AND binds tighter than OR because it's deeper in the descent chain — flattening to a Pratt parser must preserve this; (2) `NOT NOT` cancels pairwise AT PARSE TIME so evaluation never sees stacked negations beyond one; (3) depth limit counts nesting not terms.
**Probe:** `crates/filter-parser/src/lib.rs` tests `parse` (:1155-1297 — precedence/NOT/geo/_vectors/_foreign snapshots) + `error` (:1300+). GREEN at pin (`cargo test -p filter-parser --lib` = 11 passed, executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "IndexFilterCondition parse_or parse_and parse_not MAX_FILTER_DEPTH", limit: 10 });
```

## Verdict
Adopt the descent-chain precedence encoding, cut-points after keywords, parse-time NOT cancellation, and nesting-based depth cap; adapt error types; omit the geo reserved-word error parsers unless porting diagnostics too.
