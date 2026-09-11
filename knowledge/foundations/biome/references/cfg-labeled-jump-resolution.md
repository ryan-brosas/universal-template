<!-- capsule-v2 -->
# CFG labeled break/continue resolution — how do jump statements find their target without a symbol table?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does `break outer` resolve to the right block, and why can it never escape its own function?

## Bounded reverse-stack scan with label matching
**Path/Symbol:** `crates/biome_js_analyze/src/services/control_flow/nodes/break_stmt.rs:BreakVisitor.enter` (:20-76), `nodes/continue_stmt.rs:ContinueVisitor.enter` (:17-68); target providers: BlockVisitor (`block.rs:10-49`), loop/switch visitors' `pub(super) break_block/continue_block/label` fields.
**Signature:** scan: `state.stack.iter().rev().take_while(|(type_id, _)| *type_id != TypeId::of::<VisitorAdapter<FunctionVisitor>>()).find_map(|(type_id, index)| { …try_downcast::<ForVisitor|ForInVisitor|ForOfVisitor|WhileVisitor|DoWhileVisitor|SwitchVisitor>(…)… }) -> Option<BlockId>`, errors as `.ok_or(SyntaxError::MissingRequiredChild)?`.
**Data Shape:** each candidate visitor exposes `(Option<JsSyntaxToken>, BlockId)`; BlockVisitor's is nested `Option<(JsSyntaxToken, BlockId)>` (only labeled blocks participate).

### Decisive source
```rust
// break_stmt.rs:56-69 — label pairing rules: both present must match by
// trimmed text; both absent = innermost unlabeled target; mismatch keeps
// scanning outward; exhaustion is a LOUD parse-level error
match (block_label, &label) {
    (Some(a), Some(b)) => if a.text_trimmed() == b.text_trimmed() { Some(block) } else { None },
    (None, None) => Some(block),
    _ => None,
})
.ok_or(SyntaxError::MissingRequiredChild)?;
builder.append_jump(false, break_block).with_node(node.into_syntax());
```

**Flow:** walk frames innermost→outermost, stopping AT the function frame → per frame try_downcast to the seven breakable kinds → first label-compatible hit wins → append unconditional Jump carrying the break/continue statement node. ContinueVisitor differs only in its kind list (loops only — no switch/block) and field (`continue_block`).
**Invariant:** The `take_while(TypeId != FunctionVisitor)` bound makes cross-function jumps structurally impossible — no validation needed later. Labeled BLOCKS are break targets but never continue targets. Unresolvable labels abort graph construction via the error-poisoning protocol (see cfg-visitor-orchestrator), they never silently mis-target.
**Probe:** `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/{JsBreakStatement,JsLabeledStatement}.js(+.snap)` pin labeled/unlabeled resolution.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "BreakVisitor", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the bounded-scan + text-trimmed label matching verbatim. Adapt the downcast ladder to your visitor set. Omit nothing.
