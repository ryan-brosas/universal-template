<!-- capsule-v2 -->
# Import attribute list with duplicate-key tracking — how does a ParseSeparatedList carry per-list mutable state for error checking?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** `import x from "m" with { type: "json", type: "html" }` must flag the duplicate key with both ranges — where does that state live given the list trait has no obvious place for it?

## ImportAssertionList (self-referential struct + ParseSeparatedList)
**Path/Symbol:** `crates/biome_js_parser/src/syntax/module.rs:parse_import_attribute` (:534-559), `struct ImportAssertionList` (:561-599), `parse_import_attribute_entry` (:601-659).
**Signature:** `#[derive(Default)] struct ImportAssertionList { assertion_keys: FxHashMap<String, TextRange> }` implementing `ParseSeparatedList`; entries receive `&mut self.assertion_keys`.
**Data Shape:** Key normalization accepts three token shapes: string literals (quotes trimmed), identifiers, and keywords — the latter bumped via `p.bump_remap(T![ident])` so `with { type: … }` works though `type` lexes as a keyword. Value is always a string literal.

### Decisive source
```rust
let mut valid = true;
if let Some(key) = key {
    if let Some(first_use) = seen_assertion_keys.get(&key) {
        p.error(duplicate_assertion_keys_error(p, &key, *first_use, key_range));
        valid = false;
    } else {
        seen_assertion_keys.insert(key, key_range);
    }
}
// ... after completing:
let mut entry = m.complete(p, JS_IMPORT_ASSERTION_ENTRY);
if !valid { entry.change_to_bogus(p); }
```

**Flow:** `parse_import_attribute` guards on no preceding line break (ASI safety: a newline before `with`/`assert` means it's not an attribute clause) and on the `with` keyword only (`assert` is checked at :538 but only `with` proceeds — legacy `assert` clauses fall to Absent here) → start marker → expect `{` → run `ImportAssertionList::default().parse_list(p)` so each entry can consult/update the shared map → complete `JS_IMPORT_ASSERTION`.
**Invariant:** State lives in the *list struct itself*, not parser state — the map dies with the list, so nothing leaks between import statements. Duplicates demote only the offending entry to bogus; first occurrence stays intact. Keyword keys must be remapped to `ident` or the CST kind pollutes downstream consumers. Missing-key recovery (:623-629) emits at the `:` and continues rather than abandoning, keeping the rest of the list parseable.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/import_attribute.js` (`hasOwnProperty: "true"` keyword-ish keys) vs `error/import_attribute_err.js` (duplicate `type` keys, bare `with`, non-string values).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ImportAssertionList assertion_keys parse_import_attribute_entry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt stateful list structs for any separated list needing cross-element checks (duplicate names, ordering); adapt the key-normalization rules; omit the line-break gate if the host grammar has no ASI. Coverage caveat: full-mode index, metadata_match.
