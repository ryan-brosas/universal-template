<!-- capsule-v2 -->
# Condition operators & vector filters — how do IS NULL / CONTAINS / _vectors parse into the Condition enum?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How are multi-word operators (IS NOT NULL, NOT CONTAINS, STARTS WITH) and `_vectors.<embedder>` dotted paths parsed, and which negations become Not wrappers?

## parse_condition + operator family
**Path/Symbol:** `crates/filter-parser/src/condition.rs` (`Condition` enum :22-35, `parse_condition` :57-72, `parse_is_null`/`parse_is_not_null` :75-88, `parse_exists` family :107-118, `parse_vectors` :120-180, `parse_contains` family :203-225, `parse_starts_with` family :228-253, `parse_to` :256-261).
**Signature:** `fn parse_condition(input: Span) -> IResult<FilterCondition>` with `alt((tag("<="), tag(">="), tag("!="), tag("<"), tag(">"), tag("=")))`; `fn parse_vectors(input: Span) -> IResult<(Token, Option<Token>, VectorFilter)>`.
**Data Shape:** `Condition::{GreaterThan, GreaterThanOrEqual, Equal, NotEqual, Null, Empty, Exists, LowerThan, LowerThanOrEqual, Between{from,to}, Contains{keyword,word}, StartsWith{keyword,word}}`; negated forms wrap in `FilterCondition::Not(Box::new(...))` rather than dedicated variants.

### Decisive source
```rust
// condition.rs:83-88 — "IS NOT NULL" is parsed as Not(IS NULL), not its own variant
pub fn parse_is_not_null(input: Span) -> IResult<FilterCondition> {
    let (input, key) = parse_value(input)?;
    let (input, _) = tuple((tag("IS"), multispace1, tag("NOT"), multispace1, tag("NULL")))(input)?;
    Ok((input, FilterCondition::Not(Box::new(FilterCondition::Condition { fid: key, op: Null }))))
}

// condition.rs:130-138 — after "_vectors." every error is FINAL (explicit failure, not cut)
if let Ok((_, space)) = tag::<_, _, ()>(" ")(input) {
    return Err(crate::Error::failure_from_kind(
        space.into(), ErrorKind::VectorFilterMissingEmbedder));
}
```

**Flow:** Comparison conditions are single tokens (`value op value`, right side cut); BETWEEN is `value value "TO" value` (fid, from, TO, to — no operator symbol); EXISTS/CONTAINS/STARTS WITH have NOT twins that wrap the positive form in `Not`; NULL/EMPTY likewise. `_vectors` parses the reserved field name, then either whitespace (bare `_vectors EXISTS`) or `.embedder[.fragments.name | .userProvided | .documentTemplate | .regenerate]`, with explicit Failure errors for missing embedder/fragment/unknown suffix; embedder names may be quoted (dots/spaces legal inside quotes). Note `tag("STARTS WITH")` matches the literal space-containing keyword.
**Invariant:** (1) Evaluators must treat `Not(Null)` identically whether the user wrote `IS NOT NULL` or `NOT x IS NULL` — they produce the SAME tree; (2) `_geoRadius` takes an optional 4th resolution arg `(3..=4)` while `_geoBoundingBox` requires exactly 2 pairs (enforced at parse); (3) after `_vectors.` the grammar commits — partial matches never fall through to other primaries.
**Probe:** `crates/filter-parser/src/lib.rs` test `parse` (:1200-1245 NULL/EMPTY/EXISTS/CONTAINS/STARTS WITH snapshots incl double-negation collapse; :1215-1224 `_vectors.*` forms). GREEN at pin (`cargo test -p filter-parser --lib` executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "parse_condition Condition parse_vectors_exists contains starts_with", limit: 10 });
```

## Verdict
Adopt the Not-wrapping negation scheme and the commit-after-dot vector path; adapt keyword spellings if host differs; omit geojson/cellulite evaluation specifics (milli-side).
