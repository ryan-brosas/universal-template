<!-- capsule-v2 -->
# Binding-legality gate — where do eval/arguments, let, yield/await, and duplicate-binding checks live when parsing a single identifier?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** Which of the many JS binding restrictions are checked at the identifier node itself versus by the enclosing declaration's state, and how do they compose without double-erroring?

## parse_identifier_binding + object property take/restore
**Path/Symbol:** `crates/biome_js_parser/src/syntax/binding.rs:parse_identifier_binding` (:64-140), `parse_binding_pattern` (:18-26), `ObjectBindingPattern::parse_property_pattern` (:270-301).
**Signature:** `fn parse_identifier_binding(p: &mut JsParser) -> ParsedSyntax` (metavariable early-out first).
**Data Shape:** Reads parser state: `strict: Option<StrictMode>`, `duplicate_binding_parent: Option<&'static str>`, `name_map: IndexMap<String, TextRange>`; writes back into `name_map` (first declaration records its range for the "second declaration" detail).

### Decisive source
```rust
// shorthand-vs-named disambiguation in object patterns:
let kind = if p.at(T![=])
    || ((is_at_identifier_binding(p) || is_at_metavariable(p)) && !p.nth_at(1, T![:]))
{ parse_binding(p); JS_OBJECT_BINDING_PATTERN_SHORTHAND_PROPERTY }
else { parse_object_member_name(...); p.expect(T![:]); parse_binding_pattern(...); ..PROPERTY };

// the subtle one: initializer identifiers must NOT join the declaration's name map
let parent = p.state_mut().duplicate_binding_parent.take();
parse_initializer_clause(p, ExpressionContext::default()).ok();
p.state_mut().duplicate_binding_parent = parent;
```

**Flow:** parse identifier → if bogus already, stop → strict-mode `eval`/`arguments` → bogus → if inside a `let`/`const`/`import` (`duplicate_binding_parent`): `let` name itself is illegal; then `name_map` lookup errors with *both* ranges and converts to bogus; only legal bindings insert into the map.
**Invariant:** Checks run in this order so each illegal form produces exactly one diagnostic. The duplicate check consults `duplicate_binding_parent`, which is why an object-pattern *initializer* temporarily takes it aside (`const { value, f = (value) => value } = item` must not flag the arrow param) — forgetting the take/restore makes every initializer identifier a false duplicate. Rest properties demote any non-identifier inner pattern to `JS_BOGUS_BINDING` but suppress the extra error when it's already bogus (:324-334) — one error per token span, ever.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/binding_identifier_invalid.js` (pins `let await = 5` in async-arrow body, `let let = 5`, `let a, a`) and `ok/destructuring_initializer_binding.js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_identifier_binding duplicate_binding_parent name_map", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `syntax.binding.parse_identifier_binding` (:64-140).

## Verdict
Adopt centralizing per-identifier legality at the identifier production with state-supplied context; adapt the reserved-name table to the host language; omit the metavariable branch outside templating hosts. Coverage caveat: full-mode index, metadata_match. Companion seam: `references/duplicate-binding-scope.md` covers the declarator-level name_map lifecycle.
