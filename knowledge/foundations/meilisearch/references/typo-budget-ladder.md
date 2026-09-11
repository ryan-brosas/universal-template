<!-- capsule-v2 -->
# Typo budget ladder — how many typos does a query word get?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** A porter must decide, per query word, whether it allows 0/1/2 typos — where do length thresholds, exact-words, and global disable interact, and is length measured in bytes or chars?

## Typo-budget closure over settings
**Path/Symbol:** `crates/milli/src/search/new/query_term/parse_query.rs:number_of_typos_allowed` (:204-225); settings getters `crates/milli/src/index.rs:min_word_len_one_typo`/:1572, `min_word_len_two_typos`/:1595.
**Signature:** `pub fn number_of_typos_allowed<'ctx>(ctx: &SearchContext<'ctx>) -> Result<impl Fn(&str) -> u8 + 'ctx>`
**Data Shape:** Reads three persisted index settings (`authorize_typos: bool`, `min_word_len_one_typo: u8`, `min_word_len_two_typos: u8`, defaults 5/9) plus the optional `exact_words` FST. Returns a **closure** capturing the read txn; callers treat it as `Fn(&str) -> u8`.

### Decisive source
```rust
Ok(Box::new(move |word: &str| {
    if !authorize_typos
        || word.chars().count() < min_len_one_typo as usize
        || exact_words.as_ref().is_some_and(|fst| fst.contains(word))
    {
        0
    } else if word.chars().count() < min_len_two_typos as usize {
        1
    } else {
        2
    }
}))
```

**Flow:** authorize_typos=false OR char-count < one-typo threshold OR word ∈ exact_words ⇒ 0; else < two-typo threshold ⇒ 1; else 2.
**Invariant:** Length is `word.chars().count()` (**chars, not bytes**) — a Cyrillic 5-char word gets the same budget as ASCII "doggy". The exact_words check runs *inside* the per-word closure, so an exact word never derives typos even when typos are globally authorized.
**Probe:** `crates/milli/src/search/new/query_term/parse_query.rs:test_unicode_typo_tolerance_fixed` (:409-442) pins ASCII==Cyrillic at 1 typo for 5-char words under default settings; sibling `test_various_unicode_scripts` (:445-478) covers accented scripts.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "number_of_typos_allowed", limit: 5 });
```

## Verdict
Adopt the three-way ladder and chars-not-bytes semantics verbatim; adapt thresholds to host settings storage; omit the LMDB main-key plumbing. Direct tests exist and pass at HEAD (parse_query suite 3/3 GREEN).
