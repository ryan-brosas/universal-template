<!-- capsule-v2 -->
# CFG builder kernel — how do you build a control-flow graph incrementally over a syntax tree while keeping every jump target valid?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What allocation/cursor discipline must a porter preserve so block ids stay stable and the finished graph is always well-formed?

## FunctionBuilder cursor discipline
**Path/Symbol:** `crates/biome_control_flow/src/builder.rs:FunctionBuilder` (:27-41 struct, `new` :35-41, `append_block` :52-85, `cursor`/`set_cursor` :88-96, `finish` :44-49); `crates/biome_control_flow/src/lib.rs:ControlFlowGraph` (:17-51), `BasicBlock` (:61-80), `InstructionKind` (:98-117), `ROOT_BLOCK_ID` (`builder.rs:22`).
**Signature:** `pub struct FunctionBuilder<L: Language> { result: ControlFlowGraph<L>, exception_target: Vec<ExceptionHandler>, block_cursor: BlockId }`; `BlockId { index: u32 }`; `pub fn append_block(&mut self) -> BlockId`; `pub fn set_cursor(&mut self, block: BlockId)`; `fn append_instruction(&mut self, kind: InstructionKind) -> InstructionBuilder<'_, L>`; `InstructionBuilder::with_node(self, node) -> Self`.
**Data Shape:** `ControlFlowGraph { blocks: Vec<BasicBlock<L>>, node: SyntaxNode<L> }`; `BasicBlock { instructions: Vec<Instruction<L>>, exception_handlers: Vec<ExceptionHandler>, cleanup_handlers: Vec<ExceptionHandler> }`; `InstructionKind::{Statement, Jump{conditional, block, finally_fallthrough}, Return}`; `ExceptionHandler { kind: Catch|Finally, target: BlockId }`. `BlockId.index` IS the position in `blocks`.

### Decisive source
```rust
// builder.rs:44-49
pub fn finish(mut self) -> ControlFlowGraph<L> {
    // Append the implicit return instruction that resumes execution of the
    // parent procedure when control flow reaches the end of a function
    self.append_return();
    self.result
}
// builder.rs:112-120 — instructions land at the CURSOR block's tail,
// wherever the cursor currently points (enables back-patching old blocks)
fn append_instruction(&mut self, kind: InstructionKind) -> InstructionBuilder<'_, L> {
    let index = self.block_cursor.index as usize;
    let block = &mut self.result.blocks[index];
    let index = block.instructions.len();
    block.instructions.push(Instruction { kind, node: None });
    InstructionBuilder(&mut block.instructions[index])
}
```

**Flow:** `new()` seeds `blocks = [root]` (`ControlFlowGraph::new`, lib.rs:25-30) → visitors call `append_block()` (allocates next u32 id, snapshotting current exception handlers — see cfg-exception-handler-snapshot) → `set_cursor` teleports the insertion point (forward to fresh blocks, BACKWARD to entry blocks) → `append_statement/jump/return` push at the cursor tail; `.with_node()` attaches the optional syntax element afterwards → `finish()` appends the single implicit `Return`.
**Invariant:** `get(id)` indexes `self.blocks[id.index]` unchecked (lib.rs:33-37 SAFETY comment) — a porter MUST keep BlockId ≡ vec index forever (no compaction, no reuse). Blocks may be created far ahead of being filled (all visitors do this); unfilled blocks are legal until `finish`. The cursor is a single mutable register — every `set_cursor` clobbers it, so visitors save their own entry ids. Exactly one trailing `Return` exists, added only by `finish`.
**Probe:** No `#[test]` in the crate (verified: `grep -c '#\[test\]' crates/biome_control_flow/src/*.rs` = 0) — behavior is pinned downstream by lint fixtures: `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/*.js` (+`.snap`) exercise real graphs; `crates/biome_js_analyze/tests/specs/correctness/noUnreachableSuper/*.js` pin member-root graphs. Coverage caveat: builder itself is test-free upstream; treat fixture suites as its indirect probe.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "FunctionBuilder", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the id≡index contract, cursor teleport discipline, and finish-time implicit return verbatim. Adapt the language generic `L` to your CST. Omit the mermaid `Display` impls (lib.rs:131-298 — debug tooling).
