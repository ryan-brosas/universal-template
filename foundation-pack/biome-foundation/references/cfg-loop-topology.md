<!-- capsule-v2 -->
# CFG loop block topology — where do continue and break targets live in each loop form?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you lay out cond/continue/break/body blocks per loop kind so `continue` re-checks the condition exactly once?

## For/While/DoWhile visitor block layouts
**Path/Symbol:** `crates/biome_js_analyze/src/services/control_flow/nodes/for_stmt.rs:ForVisitor` (:10-104), `nodes/while_stmt.rs:WhileVisitor` (:10-79), `nodes/do_while.rs:DoWhileVisitor` (:10-79).
**Signature:** each stores `pub(super) label: Option<JsSyntaxToken>, pub(super) continue_block: BlockId, pub(super) break_block: BlockId` (+ private cond/body ids); label captured via `node.parent::<JsLabeledStatement>()` at enter.
**Data Shape:** public fields are the contract consumed by BreakVisitor/ContinueVisitor; private fields (cond_block, loop_block, body_block) are internal wiring.

### Decisive source
```rust
// while_stmt.rs:50-63 — the continue block OWNS the conditional jump;
// the body falls through to continue at exit; break follows the false arm
builder.append_jump(false, continue_block);          // end of body
builder.set_cursor(continue_block);
builder
    .append_jump(true, loop_block)
    .with_node(node.test()?.into_syntax());
builder.append_jump(false, break_block);
```
```rust
// for_stmt.rs:23-45 (enter) — for pre-allocates ALL FOUR blocks up front:
// initializer statement → cond → unconditional jump to it → continue
// (update + jump back to cond) → break → THEN park cursor in body
let cond_block = builder.append_block();
builder.append_jump(false, cond_block);
let continue_block = builder.append_block();
let break_block = builder.append_block();
builder.set_cursor(continue_block);
if let Some(update) = node.update() { …append_statement… }
builder.append_jump(false, cond_block);
```

**Flow:** **while** = enter{continue,break alloc; jump→continue; cursor→body} / exit{body→continue jump; continue: test?body : break} — continue target sits BEFORE the test. **for** = same shape but with an initializer Statement in the entry block and update Statement inside continue. **do-while** = enter allocates BODY first, jumps to it unconditionally (pre-test!), then continue/break; exit wires body→continue, continue: test?body : break.
**Invariant:** In all three forms the continue target is a distinct block that holds (or precedes) the condition re-evaluation — `continue` must never bypass the update (for) or the test (while/do-while). The end-of-body implicit jump goes to CONTINUE, not directly to cond. Break block is the sole post-loop join point; exit always leaves the cursor there so following statements append after the loop.
**Probe:** Per-kind fixtures pinning reachability through every loop shape: `crates/biome_js_analyze/tests/specs/correctness/noUnreachable/{JsForStatement,JsWhileStatement,JsDoWhileStatement,JsContinueStatement}.js(+.snap)` (23 fixtures total in the suite).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "WhileVisitor", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the three layouts verbatim — they are small but their block ordering is the whole contract. Adapt statement attachment points if your AST names differ (initializer/update/test). Omit nothing.
