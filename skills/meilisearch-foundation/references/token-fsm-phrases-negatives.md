<!-- capsule-v2 -->
# Query tokenizer FSM — phrases, negatives, prefixes, ngram synthesis

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How does a raw token stream become LocatedQueryTerms — where exactly do quoted phrases start/end, how do `-` negatives attach, and which word becomes a prefix query?

## located_query_terms_from_tokens
**Path/Symbol:** `crates/milli/src/search/new/query_term/parse_query.rs:located_query_terms_from_tokens` (:28-202), `PhraseBuilder` (:302-364), `make_ngram` (:227-300); tokenizer assembly `search/new/mod.rs:extract_tokens` (:918-996).
**Signature:** `pub fn located_query_terms_from_tokens(ctx, tokenizer, query: NormalizedTokenIter, words_limit: Option<usize>) -> Result<ExtractedTokens>`
**Data Shape:** Returns `ExtractedTokens { query_terms: Vec<LocatedQueryTerm>, graph: QueryGraph, negative_words: Vec<Word>, negative_phrases: Vec<LocatedQueryTerm> }`. Token stream capped at MAX_TOKEN_COUNT=1_000; optional words_limit truncates terms early.

### Decisive source
```rust
} else if peekable.peek().is_some() {          // NOT the last token ⇒ non-prefix word
    ... partially_initialized_term_from_word(ctx, tokenizer, word, nbr_typos(word), false, false)?
} else {                                        // LAST token ⇒ prefix (if allowed)
    ... partially_initialized_term_from_word(ctx, tokenizer, word, nbr_typos(word), allow_prefix_search, false)?
}
...
negative_next_token = phrase.is_none() && token.lemma() == "-" && encountered_whitespace;
// hard separator INSIDE a phrase closes it and immediately opens a new one:
if separator_kind == SeparatorKind::Hard {
    if let Some(phrase) = phrase { if let Some(t) = phrase.build(ctx) {
        if negative_phrase { negative_phrases.push(t); } else { query_terms.push(t); }
    }}
    Some(PhraseBuilder::empty())   // note: negative_phrase intentionally NOT reset
}
```

**Flow:** Word/StopWord tokens advance position; the LAST non-separator token gets is_prefix=allow_prefix_search (prefix search only ever on the final term); `"` toggles PhraseBuilder (stop words inside become None placeholders); unclosed quote ⇒ rest of query is the phrase; `-` right after whitespace marks the NEXT word/phrase negative (excluded via resolve_negative_words/phrases); make_ngram joins consecutive single words with NO separator between them (`words.join("")`).
**Invariant:** (1) Prefix-ness is decided by STREAM POSITION (peekable.peek()), not by syntax — a trailing space does not change it; (2) stop words are skipped as terms but still occupy positions inside phrases only; (3) a hard separator inside a quoted phrase SPLITS the phrase in two and carries the negative flag into the second half without resetting it; (4) ngrams inherit is_prefix from their LAST component and lose exact_term status (`exact_term` returns None for ngram_words.is_some()).
**Probe:** `crates/milli/src/search/new/query_term/parse_query.rs:start_with_hard_separator` (:386-406) + the split-words suite GREEN at HEAD; end-to-end negative-operator behavior pinned by meilisearch integration tests outside milli (caveat noted).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "located_query_terms_from_tokens", limit: 5 });
```

## Verdict
Adopt the token-FSM (quote buffer, negative latch, last-token-prefix rule); adapt charabia tokenizer to host NLP; omit locale allow-list plumbing.
