<!-- capsule-v2 -->
# Enum member list — how does an enum body tolerate numeric names, private names, computed names, and trailing commas while staying recoverable?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do I port TS enum-body parsing so that every invalid member form yields a positioned diagnostic and a bogus node without killing the rest of the list?

## parse_ts_enum_member + TsEnumMembersList
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/statement.rs:parse_literal_as_ts_enum_member` (:27-48), `parse_ts_enum_member` (:51-75), `TsEnumMembersList` (:76-111), `parse_ts_enum_id` (:118-155), `parse_ts_enum_declaration` (:176-200).
**Signature:** `fn parse_ts_enum_member(p: &mut JsParser) -> ParsedSyntax`; list struct implements `ParseSeparatedList` with `LIST_KIND = TS_ENUM_MEMBER_LIST`, separator `,`, trailing allowed.
**Data Shape:** Member name forks three ways: `[` → computed member name (reuses object.rs), `#` → private-name ERROR + parsed-then-bogus node, else literal path (string/ident bump; keyword remapped `T![ident]`; number → named error + `m.abandon` → Absent). Initializer clause optional, parsed with default ExpressionContext.

### Decisive source
```rust
JS_NUMBER_LITERAL => {                       // numeric member NAME is illegal
    let err = p.err_builder("An enum member cannot have a numeric name", p.cur_range());
    p.error(err); m.abandon(p); return Absent;
}
t if t.is_keyword() => p.bump_remap(T![ident]),   // `enum E { type }` — keyword AS name
```
Recovery set of the separated list:
```rust
parsed_element.or_recover_with_token_set(p,
    &ParseRecoveryTokenSet::new(JS_BOGUS_MEMBER,
        STMT_RECOVERY_SET.union(token_set![JsSyntaxKind::IDENT, T![,], T!['}']]))
    .enable_recovery_on_line_break(),
    expected_ts_enum_member)
```
Reserved-name check happens on the enum ID, not members:
```rust
let text = p.text(id.range(p));
if is_reserved_enum_name(text) { /* "`{text}` cannot be used as a enum name…" */ }
```
Missing-name fork keeps `{` anchored:
```rust
Absent => if p.nth_at(1, L_CURLY) {          // `enum 1 {...}` → bogus binding, continue body
        let m = p.start(); p.bump_any(); m.complete(p, JS_BOGUS_BINDING); …
    } else { /* "`enum` statements must have a name" spanning enum..cur */ }
```

**Flow:** `parse_ts_enum_declaration` eats optional `const` → expects `enum` → `parse_ts_enum_id` (with reserved-word diagnostic + two-way missing-name recovery) → expect `{` → `ParseSeparatedList` loop of members separated by `,` with trailing comma allowed → expect `}`.
**Invariant:** Keyword member names must be REMAPPED to ident (kind change, not error); numeric names error-and-abandon the member marker so the list-level recovery consumes the token as `JS_BOGUS_MEMBER` instead. `const enum` detection lives in the caller predicate (`T![const] => p.nth_at(n+1, T![enum])`), not here — a porter who puts it in the declaration parser breaks `const x = …`. Trailing comma MUST be allowed (`allow_trailing_separating_element == true`).
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/typescript_enum.ts` (`enum B { a, b, c }`, `const enum C { A = 1, B = A * 2, ["A"] = 3, }` incl. trailing comma + computed name) and `…/error/typescript_enum_incomplete.ts` (unclosed body) and `…/ok/ts_export_declare.ts` sibling `declare` coverage; reserved-name pin: `…/error/interface_cannot_be_reserved_world.ts` family uses the same `is_reserved_type_name` table.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_ts_enum_declaration TsEnumMembersList", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way name fork + remap-keywords rule + bogus-member recovery set; adapt the reserved-word table to host keywords; omit the `const`-enum prefix if your language lacks const enums.
