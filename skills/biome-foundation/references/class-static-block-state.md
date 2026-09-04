<!-- capsule-v2 -->
# Static initialization block state scoping — which parser state does `static { … }` enter, and why can't it use the statement-list default?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** A static block's body is statements at class scope where `await` is forbidden but the enclosing method's async/generator flags must not leak in — how is that context carved out?

## parse_static_initialization_block_class_member + EnterClassStaticInitializationBlock
**Path/Symbol:** `crates/biome_js_parser/src/syntax/class.rs:is_at_static_initialization_block_class_member` (:945-947), `parse_static_initialization_block_class_member` (:957-985); state change `crates/biome_js_parser/src/state.rs:EnterClassStaticInitializationBlock`; sibling contexts `EnterClassPropertyInitializer`, `EnterParameters(SignatureFlags)`.
**Signature:** `fn parse_static_initialization_block_class_member(p, member_marker: Marker, modifiers: ClassMemberModifiers) -> CompletedMarker`.
**Data Shape:** Detection is a strict two-token lookahead (`static` immediately followed by `{`) — this is what disambiguates from a member *named* `static`. The body parses via `parse_statements(p, true, statement_list)` inside the scoped state.

### Decisive source
```rust
if modifiers.is_empty() {
    modifiers.abandon(p);
} else {
    p.error("Static class blocks cannot have any modifier.");
    modifiers.validate_and_complete(p, JS_STATIC_INITIALIZATION_BLOCK_CLASS_MEMBER);
}
p.expect(T![static]);
p.expect(T!['{']);
p.with_state(EnterClassStaticInitializationBlock, |p| {
    let statement_list = p.start();
    parse_statements(p, true, statement_list)
});
p.expect(T!['}']);
member_marker.complete(p, JS_STATIC_INITIALIZATION_BLOCK_CLASS_MEMBER)
```

**Flow:** member dispatch checks static-block *before* modifier-driven member parsing (only after modifiers are consumed — they're abandoned or completed against the block kind) → scoped state entry → statement list with direct-expression handling → close.
**Invariant:** The block participates in the deferred-modifier protocol like any member: an empty modifier list must be *abandoned* (no node), an illegal one completed-against-the-member-kind so the error carries a range (:962-974). Property initializers and static blocks each push their own `ParsingContextFlags` delta (`EnterClassPropertyInitializer` vs `EnterClassStaticInitializationBlock`), demonstrating the per-production state-carving pattern from `references/js-parser-state.md`: the initializer path forbids `await`/`yield` differently from the block path. Getter/setter parameters similarly wrap `EnterParameters(SignatureFlags::empty())` around exactly the parameter production (:775-798) — never the whole accessor.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/static_initialization_block_member.js` (pins `static { this.a = "test"; }`) and `error/ts_class_initializer_with_modifiers.ts` (`public static { }` single diagnostic).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "EnterClassStaticInitializationBlock parse_statements static block", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt minimal-scope state deltas around exactly the productions whose [±Await]/[±Yield] parameters differ; adapt flags; omit the modifier-list ceremony if your grammar has no member modifiers. Coverage caveat: full-mode index, metadata_match.
