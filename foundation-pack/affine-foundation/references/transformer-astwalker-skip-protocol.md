<!-- capsule-v2 -->
# ASTWalker skip protocol — how does a converter prune subtrees or resume mid-list during generic traversal?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** What are the exact semantics of skipAllChildren vs skipChildren, and why does the array loop start at `_skipChildrenNum`?

## Visitor with enter/leave and two skip granularities
**Path/Symbol:** `blocksuite/framework/store/src/adapter/base.ts:225-324` (`ASTWalker`, estree-walker port); `_visit` :232-292; context flags `adapter/context.ts:14-16,112-118`.
**Signature:** `setEnter(fn)`, `setLeave(fn)`, `setONodeTypeGuard(fn)`, `walk(oNode, tNode): Promise<TNode>`, `walkONode(oNode)` (no target stack).
**Data Shape:** `NodeProps<ONode> = { node, next?, parent, prop: Keyof | null, index: number | null }` — next/index give list position to the visitor.

### Decisive source
```ts
// base.ts:234-246 + 252-257 — flags reset per visit; array iteration RESUMES past skipped children
this.context._skipChildrenNum = 0;
this.context._skip = false;
if (this._enter) await this._enter(o, this.context);
if (this.context._skip) {
  if (this._leave) await this._leave(o, this.context);
  return;                                  // subtree pruned, leave still runs
}
for (const key in o.node) {
  const value = o.node[key];
  if (value && typeof value === 'object') {
    if (Array.isArray(value)) {
      for (let i = this.context._skipChildrenNum; i < value.length; i += 1) { ... }
```

**Flow:** `walk` opens the root target then `_visit`s the source; for every object/array member passing the type guard it recurses carrying `{parent, prop, index}`. Enter callbacks create target frames (`openNode`) and may call `skipChildren(n)` (ignore first n array items — used when earlier passes already consumed siblings) or `skipAllChildren()` (prune whole subtree). Leave callbacks close frames; `closeNode` attaches.
**Invariant:** (1) `_skipChildrenNum` persists ACROSS the sibling loop of ONE visit but resets on each new visit — a converter using it must consume the prefix within that same visit. (2) The single-object branch requires `_skipChildrenNum === 0` (:275) — a stale nonzero count silently disables single-child recursion, so reset discipline is structural. (3) Pruned subtrees STILL get their leave callback (the :241-244 branch) — resource cleanup must not assume leave implies visited children.
**Probe:** `grep -c 'await this._visit(' …store/src/adapter/base.ts` → `4`. And `grep -n 'unclosed nodes' …adapter/base.ts | cut -d: -f1` → `312`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "ASTWalker _visit skipAllChildren setEnter setLeave", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the estree-walker contract for generic AST→block conversion; keep the resume-at-n loop if you stream chunks. Adapt the type guard per source format. Omit the per-visit flag resets and one skipped subtree corrupts all later ones.
