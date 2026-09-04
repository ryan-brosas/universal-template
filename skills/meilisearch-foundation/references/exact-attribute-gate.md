<!-- capsule-v2 -->
# Exact-attribute gate — exact_attributes as a typo/search firewall

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** What does marking a field "exact" actually change at search time, and where does the split between exact and tolerant databases bite a porter?

## RestrictedFids + exact/tolerant database duality
**Path/Symbol:** `crates/milli/src/search/new/mod.rs:SearchContext::new` (:94-133) — exact/tolerant fid partition; `attributes_to_search_on` (:139-223); exact-attribute rule `search/new/exact_attribute.rs` (302L whole); settings source `disabled_typos_terms.rs:DisabledTyposTerms::is_exact` (:31-35).
**Signature:** `pub struct RestrictedFids { pub tolerant: Vec<(FieldId, Weight)>, pub exact: Vec<(FieldId, Weight)> }`
**Data Shape:** SearchContext carries BOTH partitions from construction; word lookups consult `exact_word_docids`/`exact_word_prefix_docids` (documents where the term matches exactly in an exact attribute) OR-ed with tolerant counterparts (`db_cache.rs:word_docids` :183-205).

### Decisive source
```rust
// SearchContext::new partitions searchable fields once:
for (_name, fid, weight) in searchable_fids {
    if exact_attributes_ids.contains(&fid) { exact.push((fid, weight)); }
    else { tolerant.push((fid, weight)); }
}
// disabled_typos_terms.rs:
pub fn is_exact(&self, word: &str) -> bool {
    // If disable_on_numbers is true, we disable the word if it contains only numbers or punctuation
    self.disable_on_numbers && word.chars().all(|c| c.is_numeric() || c.is_ascii_punctuation())
}
```

**Flow:** At index time every posting is written to BOTH the general word_docids family AND an exact_word_docids twin when the containing attribute is exact. At search time the union feeds candidates, while the EXACTNESS ranking rule uses exact_attribute docids to bucket documents whose match is exact-in-exact-field above others. attributesToSearchOn narrows lookups to restricted fids via per-fid keys (see db-cache capsule). Typo budgets additionally zero out for pure-number/punctuation words when disableOnNumbers is set.
**Invariant:** (1) Exactness is a PROPERTY OF THE FIELD, not of the query — the same query word can be exact in one attribute and tolerant in another, so candidate sets are unions and only the RANKING separates them; (2) `ExactAttribute::new()` is pushed BEFORE Exactness graph rule in pipeline assembly (two rules, not one); (3) wildcard "*" in attributesToSearchOn resets restriction entirely (universal_wildcard ⇒ None), and unknown non-wildcard fields are UserErrors listing valid/hidden fields.
**Probe:** `crates/milli/src/search/new/tests/typo.rs:test_typo_exact_attribute` (:326-429) pins that exact-attribute matches outrank tolerant ones under equal typos; `test_typo_exact_word` (:252-323) pins exact_words FST behavior. GREEN at HEAD.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "restricted_fids", limit: 5 });
```

## Verdict
Adopt field-level exact/tolerant partitioning with union-candidates + ranking-separation; adapt to host schema storage; omit heed key layouts. Direct tests exist upstream and pass at HEAD.
