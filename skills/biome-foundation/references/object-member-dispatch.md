<!-- capsule-v2 -->
# Object-member dispatch ladder — how does `{ foo }` shorthand, `{ foo(){} }` method, `{ get/set/async *foo }`, `{...spread}`, and the `{ arrow = v }` cover-error all resolve in one pass?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the dispatch order and each guard that separates object-literal member kinds — and how does the shorthand-with-initializer error still parse its RHS?

## parse_object_member ladder
**Path/Symbol:** `crates/biome_js_parser/src/syntax/object.rs:parse_object_member` (:90-257), async guard `is_parser_at_async_method_member` (:516-520), shorthand error path (:172-197).
**Signature:** `fn parse_object_member(p: &mut JsParser) -> ParsedSyntax` inside `ObjectMembersList` (`ParseSeparatedList`, trailing `,` allowed, recovery set `{, }, ;, :}` + line-break).
**Data Shape:** Kinds: `JS_SHORTHAND_PROPERTY_OBJECT_MEMBER`, `JS_METHOD_OBJECT_MEMBER` (+async/* flags), `JS_GETTER/SETTER_OBJECT_MEMBER`, `JS_PROPERTY_OBJECT_MEMBER`, `JS_SPREAD`, `JS_BOGUS_MEMBER`, metavariables.

### Decisive source
```rust
T![get] if !p.has_nth_preceding_line_break(1) && is_nth_at_type_member_name(p, 1) => parse_getter_object_member(p),
T![set] if !p.has_nth_preceding_line_break(1) && is_nth_at_type_member_name(p, 1) => parse_setter_object_member(p),
T![async] if is_parser_at_async_method_member(p) => parse_method_object_member(p),
// async guard: at 'async', NO line break before next token, next is member-name or '*'
```
```rust
if is_nth_at_reference_identifier(p, 0) && !token_set![T!['('], T![<], T![:]].contains(p.nth(1)) {
    parse_reference_identifier(p).unwrap();
    if p.at(T![=]) {
        // "Did you mean to use a `:`? An `=` can only follow a property name when
        //  the containing object literal is part of a destructuring pattern."
        p.error(…);
        p.bump(T![=]);
        parse_assignment_expression_or_higher(p, ExpressionContext::default()).ok();
        return Present(m.complete(p, JS_BOGUS_MEMBER));   // parsed THEN demoted
    }
    return Present(m.complete(p, JS_SHORTHAND_PROPERTY_OBJECT_MEMBER));
}
```

**Flow:** metavariable (unless followed by `:` — then it's a key) → get/set with name-lookahead + line-break guard → async-method guard → `...` spread (assignment expr) → `*` generator method → identifier-shorthand (excluded when next is `(`, `<`, `:` = method/generic/property) → full name-based member: `(`/`<` ⇒ method body; else expect `:` + assignment; failed name ⇒ single-token recovery toward `:`/`,` and either salvage as property or checkpoint-rewind to Absent.
**Invariant:** The shorthand exclusion set `{(: , <)}` IS the method disambiguation — `foo` alone is shorthand, `foo(` a method. Getter/setter guards require a following member NAME so `{get() {}}` (method named "get") falls through correctly; the same contextual-keyword discipline as type members. The `{arrow = …}` case must parse the RHS (arrows!) before bogus-demotion because destructuring contexts legitimately contain it — error presence depends on expression context, so recovery can't skip the tokens.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/getter_object_member.js` (`get()` = "method not a getter"), `ok/assignment_shorthand_prop_with_initializer.js` vs `error/object_shorthand_with_initializer.js`, `error/object_expr_error_prop_name.js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_object_member shorthand setter getter spread method", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered guard ladder + exclusion-set shorthand rule + parse-then-demote for context-dependent errors; adapt kinds; omit message strings. TS accessor extras (type-param ban on accessors, setter return-type ban) ride along in the getter/setter arms (:274-276, :351-358).
