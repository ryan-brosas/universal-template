<!-- capsule-v2 -->
# CFG bogus-node poisoning — how does a parser-recovery node abort graph construction for its whole function?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What should a CFG builder do when the syntax tree contains recovered/bogus nodes?

## BogusVisitor + labeled-block side seam
**Path/Symbol:** `crates/biome_js_analyze/src/services/control_flow/nodes/bogus.rs:BogusVisitor.enter` (:19-21); companion `nodes/block.rs:BlockVisitor` (:10-49) and `nodes/statement.rs:StatementVisitor` / `nodes/variable.rs:VariableVisitor` / `nodes/return_stmt.rs:ReturnVisitor` / `nodes/throw_stmt.rs:ThrowVisitor`.
**Signature:** `fn enter(_: AnyJsBogusNode, _: &mut FunctionBuilder, _: StatementStack) -> SyntaxResult<Self> { Err(SyntaxError::UnexpectedBogusNode) }` — the entire visitor body.
**Data Shape:** `AnyJsBogusNode` = the rowan bogus-node union; poisoning propagates through `VisitorAdapter` (visitor.rs:239-241) which `.take()`s the builder.

### Decisive source
```rust
// bogus.rs:14-21 — the doc comment is the contract
/// Bogus visitor.
///
/// The bogus visitor merely acts to abort control flow analysis inside broken
/// code, which could otherwise mess with assumptions made inside other
/// visitors.
impl NodeVisitor for BogusVisitor {
    fn enter(_: Self::Node, _: &mut FunctionBuilder, _: StatementStack) -> SyntaxResult<Self> {
        Err(SyntaxError::UnexpectedBogusNode)
    }
}
```

**Flow:** any bogus node anywhere in the function → enter returns Err → adapter takes the builder → all later enter/exit calls in this function see `builder = None` and no-op → FunctionVisitor::exit skips `ctx.match_query` → rules get NO ControlFlowGraph match.
**Invariant:** Fail-closed by design: broken syntax yields NO reachability verdicts, never wrong ones. A porter who instead "skips" the bogus node keeps building on corrupted assumptions (e.g. a missing else-arm flips every downstream jump). Side seams in the same plane: ThrowVisitor models `throw` as `append_return` (divergence = return-class instruction, lib.rs:113-116 documents this); VariableVisitor emits one Statement PER DECLARATOR INITIALIZER (not per statement — `var a=1,b=2` = 2 instructions, only initializers, no bare declarations); BlockVisitor allocates a break target ONLY when parented by JsLabeledStatement and patches it at exit.
**Probe:** Deterministic source pin (`bogus.rs:19-21`, quoted above). Behavioral pinning rides the fixture suites: files under `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/` never contain bogus nodes — absence of diagnostics on broken inputs is observable via `crates/biome_js_analyze/tests/specs/` suppression suites. Coverage caveat: no direct unit test for UnexpectedBogusNode.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "BogusVisitor", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt poisoning verbatim — it is the safety story of the whole subsystem. Adapt the bogus-node union to your grammar. Omit nothing.
