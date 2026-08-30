<!-- capsule-v2 -->
# Duplicate-binding name_map take/restore — how do you scope an error-accumulating map to a sub-parse without losing outer entries?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the parser detect `let a, a` duplicates while keeping each declarator's initializer from polluting the declaration's name map?

## name_map save/restore around initializers
**Path/Symbol:** `crates/biome_js_parser/src/syntax/stmt.rs:parse_variable_declarator` (:1356-1504), map lifecycle `eat_variable_declaration` (:1200-1240); field on state: `crates/biome_js_parser/src/state.rs:JsParserState.name_map` + `duplicate_binding_parent` (:93-96).
**Signature:** `let last_name_map = std::mem::take(&mut p.state_mut().name_map); ... p.state_mut().name_map = last_name_map;`
**Data Shape:** `name_map: IndexMap<String, TextRange>` (insertion-ordered, first binding wins its range), `duplicate_binding_parent: Option<&'static str>` (the keyword to name in errors: "let"/"const"/"import").

### Decisive source
```rust
p.state_mut().duplicate_binding_parent = context.kind_name;
let id = parse_binding_pattern(p, ExpressionContext::default());
p.state_mut().duplicate_binding_parent = None;
// ...
let last_name_map = std::mem::take(&mut p.state_mut().name_map);
let duplicate_binding_parent = p.state_mut().duplicate_binding_parent.take();
let mut initializer = parse_initializer_clause(/* ... */).ok();
// (initializer bindings are NOT checked against the declarator names)
p.state_mut().name_map = last_name_map;
p.state_mut().duplicate_binding_parent = duplicate_binding_parent;
```

**Flow:** per declarator: set `duplicate_binding_parent` → parse the binding pattern (which inserts into `name_map`, flagging duplicates) → clear it → `take()` the whole map aside → parse the initializer (its identifiers must not collide) → put the map back → after the full list, `eat_variable_declaration` clears the map so sibling declarations start fresh.
**Invariant:** The map is *taken*, not cloned — zero allocation, and any entries the initializer added are dropped with the taken value. `duplicate_binding_parent` uses `Option::take` for the same reason. Forgetting either restore leaks collision detection across statements (`let a; let a;` would falsely error) or across scopes.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/lexical_declaration_in_single_statement_context.js` and the `variable_declaration_statement_err` corpus (`let a, { b } = { a: 10 }` errors; initializer-only collisions don't).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "eat_variable_declaration name_map duplicate_binding", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `syntax.stmt.eat_variable_declaration` (:1200-1240).

## Verdict
Adopt mem::take/restore as the pattern for any error-accumulator scoped to a grammar region (also applies to lint-rule scope maps); adapt key types; omit TS definite-annotation checks if porting outside TS.
