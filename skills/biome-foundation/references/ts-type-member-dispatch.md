<!-- capsule-v2 -->
# Type-member dispatch + member-name lookahead — how does `{ get }` stay a property while `{ get a(): number }` becomes a getter signature, and where do commas/ASIs separate members?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What predicate ordering classifies object-type members, and how is the contextual-keyword-vs-member-name conflict resolved?

## TypeMembers ParseNodeList + parse_ts_type_member dispatch
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:TypeMembers` (:1200-1233), `parse_ts_type_member` (:1235-1265), `parse_ts_property_or_method_signature_type_member` (:1274-1313), `parse_ts_type_member_semi` (:2281-2295).
**Signature:** `impl ParseNodeList for TypeMembers` (LIST_KIND `TS_TYPE_MEMBER_LIST`, recovery set `{'}', ',', ';'}` + line-break); dispatch: index-signature check → `(`/`<` call sig → `new`+lookahead → `get`/`set`+name-lookahead → property/method.
**Data Shape:** Members: call/construct/getter/setter/property/method signature kinds. Method detection = after optional `?`, next token is `(` or `<`.

### Decisive source
```rust
T![get] if is_nth_at_type_member_name(p, 1) => parse_ts_getter_signature_type_member(p, context),
T![set] if is_nth_at_type_member_name(p, 1) => parse_ts_setter_signature_type_member(p, context),
```
```rust
// property-or-method: 'readonly' eaten only if followed by a member name
let readonly_range = if p.at(T![readonly]) && is_nth_at_type_member_name(p, 1) { … }
// method fork AFTER the name:
if p.at(T!['(']) || p.at(T![<]) {
    parse_ts_call_signature(p, context.and_allow_const_modifier(true));  // const allowed in method type params
    // … then: "readonly modifier can only appear on a property or signature declaration" retro-error
} else { /* annotation → TS_PROPERTY_SIGNATURE_TYPE_MEMBER */ }
```
Separator handling:
```rust
fn parse_ts_type_member_semi(p: &mut JsParser) {
    if p.eat(T![,]) { return; }            // comma-separated members
    if !optional_semi(p) {                  // or semicolon with ASI
        p.error("';' expected'".with_hint(…));
    }
}
```

**Flow:** each guard pairs a contextual keyword (`get`/`set`/`new`) with an nth-token lookahead for a *member name*, so `{ get: T }`, `{ get() }`, `{ get }` all fall through to plain properties. Index signatures are checked FIRST because `[a: number]: string` would otherwise look like a computed property.
**Invariant:** The lookahead-before-commit rule applies to every contextual keyword; skipping it misparses members named literally `get`/`set`. The `readonly`-on-method error fires *retroactively* using the saved range — the method still completes as its proper kind first (error-with-node, not rejection). Member separation accepts BOTH `,` and ASI'd `;` — porting only one breaks real-world `.d.ts` shapes.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_property_or_method_signature_member.ts` (`{ readonly: string, readonly a: number }`) and `ok/ts_getter_signature_member.ts` / `ok/ts_setter_signature_member.ts` ("members that look like getters but aren't").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "is_nth_at_type_member_name getter setter signature member", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt keyword-plus-following-name gating and dual `,`/ASI separators; adapt member kinds to host AST; omit message strings. Object-literal parsing shares `parse_object_member_name` via object.rs (see module capsules for the import-side consumers).
