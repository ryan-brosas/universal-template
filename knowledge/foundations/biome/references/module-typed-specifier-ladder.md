<!-- capsule-v2 -->
# Typed-import/export specifier ladder — how do you parse `{ type, type as, type as as, type as as as }` correctly when `type` and `as` are also legal names?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the parser decide whether the first token of an import/export specifier is the TS `type` modifier, whether there is an alias, and what to do when the local name was forgotten (`{ as x }`)?

## specifier_metadata decision table
**Path/Symbol:** `crates/biome_js_parser/src/syntax/module.rs:specifier_metadata` (:933-990), consumed by `parse_any_named_import_specifier` (:466-516), `parse_any_export_named_specifier` (:833-910), `parse_export_named_from_specifier` (:1127-1165); clause-level typed gate in `parse_import_clause` (:277-291).
**Signature:** `fn specifier_metadata<LocalNamePred, AliasPred>(p: &mut JsParser, is_nth_name: LocalNamePred, is_nth_alias: AliasPred) -> SpecifierMetadata` — predicates are passed per call-site because import specifiers need *binding*-name legality while export specifiers accept any literal export name.
**Data Shape:** `SpecifierMetadata { is_type: bool, has_alias: bool, is_local_name_missing: bool }` — three booleans that fully determine which tokens the caller then consumes.

### Decisive source
```rust
if p.at(T![type]) {
    if p.nth_at(1, T![as]) {
        if p.nth_at(2, T![as]) {                       // { type as as ... }
            metadata.has_alias = true;
            if is_nth_alias(p, 3) { metadata.is_type = true; }   // { type as as x }
        } else if is_nth_alias(p, 2) { metadata.has_alias = true; } // { type as x }
        else { metadata.is_type = true; }              // { type as }  -> exports name `as`
    } else {                                           // { type x } / { type x as }
        metadata.is_type = is_nth_name(p, 1) || p.nth_at(1, T![default]);
        metadata.has_alias = p.nth_at(2, T![as]);
    }
} else if p.at(T![as]) && is_nth_alias(p, 1) {
    metadata.has_alias = true;
    metadata.is_local_name_missing = !p.nth_at(1, T![as]);   // { as x } recovery
}
```
```rust
// clause level: `import type X from` vs binding named `type`; lookahead ladder:
let is_typed = 'is_typed: {
    if !p.at(T![type]) { break 'is_typed false; }
    if matches!(p.nth(1), T![*] | T!['{']) { break 'is_typed true; }
    if !is_nth_at_identifier_binding(p, 1) { break 'is_typed false; }
    !p.nth_at(1, T![from]) || p.nth_at(2, T![from])
};
```

**Flow:** compute metadata once (pure lookahead, no consumption) → caller consumes exactly the tokens the metadata implies (`type`, local name or error at a zero-width range, `as`, alias) → wrap in shorthand vs aliased kind → if `is_type`, re-check with `TypeScript.exclusive_syntax` so JS files get one ts-only diagnostic.
**Invariant:** The metadata pass must be side-effect free — callers rely on being able to consume in their own order (export-named even parses string locals it will reject, purely so the later `export {} from` rewind sees consistent state). Zero-width diagnostics (`TextRange::new(cur_start, cur_start)`) mark missing names without consuming anything. The same table serves three specifier grammars; only the injected predicates differ.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_named_import_specifier_with_type.ts` (pins all five `{type...}` shapes incl. `type "test-abcd" as test`) and `ok/ts_export_type_specifier.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "specifier_metadata SpecifierMetadata is_local_name_missing", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pure-lookahead metadata struct + predicate injection for contextual-keyword ambiguity in module specifiers; adapt the keyword set; omit the string-export error lane if the host bans string names earlier. Coverage caveat: full-mode index, metadata_match.
