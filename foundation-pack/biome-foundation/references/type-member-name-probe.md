<!-- capsule-v2 -->
# Type-member-name probe — how does ONE predicate gate `get`/`set`/`readonly` keyword disambiguation across object literals, interfaces, and class bodies?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do I decide whether a contextual keyword (`get`, `set`, `readonly`, `async`) is a MODIFIER or a MEMBER NAME without consuming tokens?

## is_nth_at_type_member_name
**Path/Symbol:** `crates/biome_js_parser/src/syntax/object.rs:is_nth_at_type_member_name` (:377-392), alias `is_at_object_member_name` (:394-396).
**Signature:** `fn is_nth_at_type_member_name(p: &mut JsParser, offset: usize) -> bool` — pure lookahead over one token, no consumption.
**Data Shape:** True iff token at offset is ANY keyword OR in `{JS_STRING_LITERAL, JS_NUMBER_LITERAL, T![ident], T![await], T![yield], T!['[']}`. Note keywords are accepted via `nth.is_keyword()` — that includes `get`, `set`, `readonly`, `type`, `new`, etc.

### Decisive source
```rust
pub(crate) fn is_nth_at_type_member_name(p: &mut JsParser, offset: usize) -> bool {
    let nth = p.nth(offset);
    let start_names = token_set![
        JS_STRING_LITERAL, JS_NUMBER_LITERAL,
        T![ident], T![await], T![yield], T!['[']
    ];
    nth.is_keyword() || start_names.contains(nth)
}
```
The disambiguation pattern it powers (types.rs member dispatch):
```rust
T![get] if is_nth_at_type_member_name(p, 1) => { /* accessor with name after */ }
T![set] if is_nth_at_type_member_name(p, 1) => { … }
let readonly_range = if p.at(T![readonly]) && is_nth_at_type_member_name(p, 1) { … };
```
Object-literal twin (object.rs:115/142) adds an ASI guard the type side lacks:
```rust
T![get] if !p.has_nth_preceding_line_break(1) && is_nth_at_type_member_name(p, 1) => …
```

**Flow:** whenever a member parser sees a contextual modifier keyword it probes offset+1: name-like ⇒ treat keyword as modifier and parse the member normally; anything else (e.g. `get;`, `set = 5`, `readonly\nname` on the object-literal side) ⇒ the keyword IS the member name.
**Invariant:** The predicate accepts ALL keywords as names — this is deliberate: `{ new(): B }` inside an interface must parse as a member named `new`, so narrowing to "identifier-like" breaks construct signatures. The object-literal call sites add `has_nth_preceding_line_break(1)` for ASI but the TS type-member sites deliberately DON'T (type members have no ASI). A porter who unifies the two either breaks `get\n()` recovery or adds spurious line-break sensitivity to interfaces.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_interface_heritage_clause_error.ts` sibling `…/ok/` interface suites pinning `[index: number]: string` computed + `new(): B` member forms; object-side pin: getter/setter specs under `…/ok/getter_*`/`setter_*`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "is_nth_at_type_member_name get set readonly member", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the all-keywords-are-names rule plus per-context ASI guards; adapt the start-name set to your token vocabulary; omit the literal-name arms if your AST models string/number member names differently.
