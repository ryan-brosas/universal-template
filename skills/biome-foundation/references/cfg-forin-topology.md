<!-- capsule-v2 -->
# CFG for-in/for-of topology — why is the loop condition an initializer-keyed jump?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you model iterator-advance semantics in a CFG when the language has no per-iteration test expression?

## ForInVisitor / ForOfVisitor
**Path/Symbol:** `crates/biome_js_analyze/src/services/control_flow/nodes/for_in.rs:ForInVisitor` (:10-70), `nodes/for_of.rs:ForOfVisitor` (:10-70) — the two files are byte-twins apart from the node type.
**Signature:** `{ label: Option<JsSyntaxToken>, continue_block: BlockId, break_block: BlockId }`; enter allocates continue→loop→break then wires; exit appends body→continue and parks cursor on break.
**Data Shape:** condition node = `node.initializer()` (the binding/target of `for (x in obj)` / `for (x of iter)`) — NOT a test.

### Decisive source
```rust
// for_in.rs:21-40 (enter) — allocation order: continue → loop → break;
// entry jumps to CONTINUE; the conditional edge is keyed on the INITIALIZER
// because "advance the iterator" IS the per-iteration test here
let continue_block = builder.append_block();
let loop_block = builder.append_block();
let break_block = builder.append_block();
builder.append_jump(false, continue_block);
builder.set_cursor(continue_block);
builder.append_jump(true, loop_block).with_node(node.initializer()?.into_syntax());
builder.append_jump(false, break_block);
builder.set_cursor(loop_block);   // body starts after wiring
```

**Flow:** entry block unconditionally jumps to continue → continue holds the conditional jump (has-next?) to loop, false arm to break → body statements append into loop → exit adds loop→continue. Identical shape for both kinds.
**Invariant:** The conditional jump's attached node is the initializer/advance, so diagnostics about iteration progress point at the binding — a porter who attaches the whole statement or omits `.with_node()` degrades every downstream diagnostic span. Continue target = the advance/test block (never the body). Cursor ends on break after exit.
**Probe:** `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/{JsForInStatement,JsForOfStatement}.js(+.snap)`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ForOfVisitor", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt verbatim as one template instantiated twice. Adapt the condition-node accessor to your AST. Omit nothing.
