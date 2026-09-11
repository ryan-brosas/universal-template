<!-- capsule-v2 -->
# Derivation computation — lazy typo/split/prefix expansion against the FST

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** When and how are a query term's one-typo/two-typo derivations computed, and what does a porter get wrong about the first-letter rule and the split-words carve-out?

## Lazy two-stage derivation engine
**Path/Symbol:** `crates/milli/src/search/new/query_term/compute_derivations.rs:compute_fully_if_needed` (:21-37), `initialize_one_typo_subterm` (:264-317), `initialize_one_and_two_typo_subterm` (:318-356), `find_one_two_typo_derivations` (:109-168), `split_best_frequency` (:363-383), `partially_initialized_term_from_word` (:170-253).
**Signature:** `fn compute_fully_if_needed(self, ctx: &mut SearchContext<'_>) -> Result<()>` on `Interned<QueryTerm>`; `fn split_best_frequency(ctx, original: &str) -> Result<Option<(Interned<String>, Interned<String>)>>`
**Data Shape:** Mutates the term in the term interner through `Lazy::Uninit → Lazy::Init`. Derivation sets are capped by `limits.rs`: MAX_PREFIX_COUNT=1_000, MAX_ONE_TYPO_COUNT=150, MAX_TWO_TYPOS_COUNT=50, MAX_SYNONYM_PHRASE_COUNT=50, MAX_SYNONYM_WORD_COUNT=100.

### Decisive source
```rust
// find_one_two_typo_derivations: ONE fst scan, automaton = Union(
//   Intersection(dfa(1), Complement(starts_with_first_char)),
//   Intersection(dfa(2), starts_with_first_char))
if get_first(derived_word) != get_first(word) && !finished_two_typo_words {
    // in the case the typo is on the first letter, we know the number of typo is two
    let derived_word_interned = word_interner.insert(derived_word.to_owned());
    two_typo_words.insert(derived_word_interned);
    continue;
}
```

**Flow:** `partially_initialized_term_from_word` computes ONLY zero-typo data at parse time (exact word membership via `contains_word`, prefix-of expansions when prefix && !use_prefix_db, synonyms, use_prefix_db flag from word_prefix_docids/exact_word_prefix_docids presence). Later, any consumer needing 1+-typo words calls `compute_fully_if_needed`: max_levenshtein ≤1 ⇒ initialize one-typo only (two stays empty default); >1 ⇒ compute both. One-typo stage also computes split words.
**Invariant:** (1) **A typo on the first character counts as TWO typos** — enforced structurally: dfa(1) is complemented with StartsWith(first-char) so it can never match first-letter variants; anything outside the first char is classified distance-2 without consulting the DFA. (2) One-typo derivations are initialized even when the budget is 0, *because of split words* (`allows_split_words()` is false only for phrases). (3) For an ngram, split words are added only if they differ from the ngram's own component words (`ngram_words.iter().ne(words.iter().flatten())`) — otherwise every joined ngram would degenerately "split" back into itself. `split_best_frequency` picks the split whose halves co-occur with proximity 1 in the most documents.
**Probe:** `crates/milli/src/search/new/tests/ngram_split_words.rs:test_split_words` (:242-261) pins that querying `sunflower ` returns both `sunflower` docs AND `sun flower` docs; `test_disable_split_words` (:266-291) shows authorize_typos=false removes the split path; direct tests GREEN at HEAD (14/14).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "split_best_frequency", limit: 5 });
```

## Verdict
Adopt lazy derivation + first-letter-counts-double + split-frequency heuristic as a unit; adapt the FST/DFA machinery to the host's string-distance index; omit heed codec specifics. Tests exist upstream and pass at HEAD.
