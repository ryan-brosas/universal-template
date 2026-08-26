<!-- capsule-v2 -->
# CFG switch fallthrough chain — how do case clauses become a linked list with a single entry fan-out?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How is JS switch modeled when cases both jump from the discriminant AND fall through to their neighbor?

## SwitchVisitor + CaseVisitor
**Path/Symbol:** `crates/biome_js_analyze/src/services/control_flow/nodes/switch_stmt.rs:SwitchVisitor` (:10-81), `CaseVisitor` (:83-120+).
**Signature:** `SwitchVisitor { entry_block: BlockId, label: Option<JsSyntaxToken>, break_block: BlockId, is_first_case_clause: bool, default_block: Option<(BlockId, JsSyntaxToken)> }`; CaseVisitor reads `stack.read_top::<SwitchVisitor>()`.
**Data Shape:** `default_block` carries the token so the entry→default jump can be labeled with the `default` keyword's span; discriminant emitted as a Statement before any block allocation.

### Decisive source
```rust
// switch_stmt.rs:88-101 (CaseVisitor::enter) — every clause allocates a
// block; non-first clauses get an explicit FALLTHROUGH edge from wherever
// the previous clause ended; case tests are back-patched onto entry_block
let case_block = builder.append_block();
if !switch_stmt.is_first_case_clause {
    builder.append_jump(false, case_block);      // fallthrough from previous
} else {
    switch_stmt.is_first_case_clause = false;
}
match node {
    AnyJsSwitchClause::JsCaseClause(node) => {
        builder.set_cursor(switch_stmt.entry_block);
        builder.append_jump(true, case_block).with_node(node.test()?.into_syntax());
    }
    AnyJsSwitchClause::JsDefaultClause(node) => {
        switch_stmt.default_block = Some((case_block, node.default_token()?));
    }
}
builder.set_cursor(case_block);
```

**Flow:** SwitchVisitor::enter emits the discriminant Statement, snapshots entry cursor, allocates break → per-clause enter wires the chain above → exit: implicit last-clause→break jump (only if ≥1 clause), then teleport to entry and emit either entry→default (`with_node(default_token)`) or entry→break.
**Invariant:** Fallthrough is an EXPLICIT edge appended at each clause boundary — never an implicit instruction-order assumption — because blocks may interleave. Default is deferred to exit: its entry-edge can only be placed after ALL case-test edges exist on the shared entry block. A switch with zero clauses gets no last-jump and falls straight to break. Labeled-switch support rides on `label`/`break_block` exactly like loops (BreakVisitor treats SwitchVisitor as a break target).
**Probe:** `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/` fixtures covering switch reachability; `crates/biome_js_analyze/src/lint/suspicious/no_fallthrough_switch_clause.rs` consumes these same edges as a second consumer proof.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "CaseVisitor", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the chain+deferred-default design verbatim. Adapt clause/test node kinds. Omit nothing.
