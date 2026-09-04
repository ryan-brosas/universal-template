<!-- capsule-v2 -->
# Tagged union — how is the discriminator read and what are the two failure shapes?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** How does tag lookup work across dict/attribute/JSON inputs, and how do missing-vs-invalid tags differ?

## Discriminator::LookupKey reads the tag BEFORE dispatch; Function discriminators may return None
**Path/Symbol:** `src/validators/union.rs:TaggedUnionValidator` (:284-421); `Discriminator` in `src/common/union.rs`; `LookupKey/LookupPath` in `src/lookup_key.rs`.
**Signature:** build takes `discriminator` (string | list-of-keys | list-of-lists) + `choices: PyDict[tag -> schema]`; `from_attributes` defaults TRUE for tagged unions (`schema_or_config(...).unwrap_or(true)` :330) unlike model-fields (false).
**Data Shape:** `lookup: LiteralLookup<Arc<CombinedValidator>>` built from `(choice_key, validator)` pairs preserving schema-dict order; `tags_repr` = reprs joined `", "`; `discriminator_repr`; name = `"tagged-union[Name1,Name2,...]"` joined with commas and NO spaces.

### Decisive source
```rust
let Some((_, tag)) = dict.get_item(lookup_key)? else {
    return Err(self.tag_not_found(input));
};
self.find_call_validator(py, &tag.borrow_input().to_object(py)?, input, state)
...
// find_call_validator miss path:
None => Err(ValError::new(ErrorType::UnionTagInvalid {
    discriminator: self.discriminator_repr.clone(),
    tag: tag.to_string(), expected_tags: self.tags_repr.clone(), context: None }, input)),
```

**Flow:** LookupKey resolves through THREE planes uniformly — python dicts, attribute access on objects (from_attributes), and JSON objects (`json_get` iterates `.iter().rev()` because jiter JsonObject dedups by LAST occurrence) via one `Simple|Choice{alias,field-name}|PathChoices` enum. Missing tag ⇒ `UnionTagNotFound` (or custom_error). Present-but-unregistered tag ⇒ `UnionTagInvalid` carrying `expected_tags`. Matched tag validates through its member; member LineErrors get the TAG as outer loc (`err.with_outer_location(tag)` :392) so errors read `('tag', 'field')`.
**Invariant:** The tag value itself can be any input type (str/int/...) — it's converted to object only for LiteralLookup matching. Discriminator functions returning None mean "cannot determine" (→ NotFound), NOT "no match". Build-time choices is a DICT (mapping form required), vs plain unions' LIST form.
**Probe:** `grep -n 'fn tag_not_found' src/validators/union.rs` =1 (:409); direct tests: tests/validators/test_tagged_union.py suite green this pass (in the 283-passed batch); `grep -c 'union_tag_not_found\|union_tag_invalid' tests/validators/test_tagged_union.py` >0.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "TaggedUnionValidator find_call_validator UnionTagInvalid", limit: 4 });
// live rank-family: TaggedUnionValidator methods line-exact in src/validators/union.rs
```

## Verdict
Adopt: pre-dispatch tag resolution over a literal lookup table, dual error taxonomy (NotFound vs Invalid with expected-tags repr), alias-or-field-name Choice lookup, tag-as-error-prefix. Adapt LookupKey's dotted-path support away if your schemas never nest discriminators. Omit function-discriminator caching (none exists — called per validation).
