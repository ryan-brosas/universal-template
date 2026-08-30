<!-- capsule-v2 -->
# ASTWalkerContext stack — how does a streaming converter attach child nodes to the right parent?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** What is the open/close protocol for building nested output nodes during a single-pass AST walk, and how do per-node vs global contexts differ?

## Stack-based parent attach + two-level context
**Path/Symbol:** `blocksuite/framework/store/src/adapter/context.ts:3-119` (`ASTWalkerContext`); attach logic :36-49 (`closeNode`); contexts :55-110.
**Signature:** `openNode(node, parentProp?)` / `closeNode(): this` / `currentNode()`; global: `setGlobalContext(key, value)`, `pushGlobalContextStack(key, value)`, `getGlobalContextStack(key)`; node: `setNodeContext(key, value)` / `getNodeContext(key)` / `getPreviousNodeContext(key)`.
**Data Shape:** stack frames = `{ node: TNode, prop: Keyof<TNode>, context: Record<string, unknown> }`; default child-collection prop is `'children'` (`_defaultProp`, :4).

### Decisive source
```ts
// context.ts:36-49 — pop child, pop parent, PUSH CHILD INTO parent[prop] if array
closeNode() {
  const ele = this._stack.pop();
  if (!ele) return this;
  const parent = this._stack.pop();
  if (!parent) {
    this._stack.push(ele);      // root: nothing to attach to
    return this;
  }
  if (parent.node[ele.prop] instanceof Array) {
    (parent.node[ele.prop] as Array<object>).push(ele.node);
  }
  this._stack.push(parent);
  return this;
}
```

**Flow:** converter's enter callback: build target node → `openNode(node, 'children' | custom prop)` → record per-node state via setNodeContext. Leave callback (reverse order): `closeNode()` — the context itself performs the parent attachment by pushing the popped node into the parent frame's array prop. Cross-subtree accumulators (e.g. collected asset ids) go in `_globalContext` (Object.create(null) — prototype-free); `pushGlobalContextStack` lazily creates the array on first push.
**Invariant:** (1) Attachment happens ONLY when the stored prop is an Array — attaching to an object prop silently no-ops, which is the documented way to say "this node has no children slot". (2) `openNode` without a matching `closeNode` desynchronizes every later attach — hence ASTWalker.walk's final unclosed-nodes throw. (3) Node context dies with its frame; anything needed after closeNode must move to global context BEFORE popping.
**Probe:** `grep -n 'parent.node\[ele.prop\] instanceof Array\|_defaultProp\|Object.create(null)' …adapter/context.ts | cut -d: -f1` → `4 6 19 44 79 80`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "ASTWalkerContext closeNode openNode skipChildren", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stack-attach pattern for any single-pass tree-to-tree converter (markdown AST→blocks is the canonical consumer). Adapt the default prop name to your node shape. Omit the array-only guard and object-typed props get corrupted by pushes.
