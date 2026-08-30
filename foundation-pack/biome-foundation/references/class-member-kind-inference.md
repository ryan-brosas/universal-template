<!-- capsule-v2 -->
# Signature-vs-declaration body inference — how does one method-body parser decide between TS_METHOD_SIGNATURE_CLASS_MEMBER and JS_METHOD_CLASS_MEMBER?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** TypeScript members are legal both with a body (`m() {}`) and as overload/abstract/ambient signatures (`m();`) — where is that decision made, and how do the error cases (missing body, body-in-ambient) stay single-diagnostic?

## expect_method_body → MemberKind
**Path/Symbol:** `crates/biome_js_parser/src/syntax/class.rs:expect_method_body` (:1432-1525), `MemberKind` + syntax-kind mapping (:1341-1379), `ClassMethodMemberKind` (:1382-1416), accessor/constructor wrappers (:1536-1579).
**Signature:** `fn expect_method_body(p, member_marker: &Marker, modifiers: &ClassMemberModifiers, method_kind: ClassMethodMemberKind) -> MemberKind`.
**Data Shape:** `ClassMethodMemberKind::{Accessor, Constructor, Method(SignatureFlags)}` — accessors never have optional bodies, constructors map to `SignatureFlags::CONSTRUCTOR`, plain methods carry ASYNC/GENERATOR flags. Returns `MemberKind::{Signature, Declaration}` which the caller feeds to `as_*_syntax_kind()`.

### Decisive source
```rust
let body = parse_function_body(p, method_kind.signature_flags());
if p.state().in_ambient_context() {
    match body { Present(b) => p.error(unexpected_body_inside_ambient_context(...)),
                 Absent => expect_member_semi(p, member_marker, "method declaration") }
    MemberKind::Signature
}
else if modifiers.has(ModifierKind::Abstract) && !method_kind.is_constructor() {
    /* same shape: body present = error; absent = require semi */ MemberKind::Signature
}
else if method_kind.is_body_optional() && TypeScript.is_supported(p) && body.is_absent() && optional_semi(p) {
    MemberKind::Signature   // TS overloads
}
else { body.or_add_diagnostic(p, expected_class_method_body); MemberKind::Declaration }
```

**Flow:** try to parse the body unconditionally → branch on ambient context first (signature regardless of abstract), then abstract modifier, then the TS-overload case (body absent *and* a semicolon/ASI actually consumed — this ordering prevents `class A { m()` from silently becoming a signature), else require the body.
**Invariant:** The decision consumes state in order: an ambient-context member with a body errors but stays a signature; the overload path requires `optional_semi()` to succeed so missing-semicolon declarations still produce "expected method body". Post-completion cross-checks ride on the flags: generator-signature error (:1313-1324), abstract+async demotion (:1306-1312), ambient async demotion (:1325-1332). `expect_member_semi` reports against the whole member range using `p.last_end().unwrap_or_else(|| p.cur_range().start())` so ASI diagnostics point at the line end.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/typescript_members_can_have_no_body_in_ambient_context.ts` vs `error/typescript_members_with_body_in_ambient_context_should_err.ts`, plus `ok/ts_method_and_constructor_overload.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "expect_method_body MemberKind ClassMethodMemberKind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-lane body inference for any language mixing signatures and implementations in one grammar; adapt the lane predicates; omit TS overload merging subtleties if the host has no overloads. Coverage caveat: full-mode index, metadata_match.
