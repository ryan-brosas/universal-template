<!-- capsule-v2 -->
# Recursive generic AST traverser — how do you walk an arbitrary AST with enter/leave, skip/break, and unknown node-type fallback?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does a standalone (non-selector) traverser descend visitor-key trees safely when the tree may contain node types it has never seen?

## shared Traverser
**Path/Symbol:** `lib/shared/traverser.js:Traverser` (:55–202) — `_traverse(node, parent)` (:130–156), `getVisitorKeys(visitorKeys, node)` (:42–52), static `traverse`/`getKeys`/`DEFAULT_VISITOR_KEYS` (:176–199).
**Signature:** `new Traverser().traverse(root, { visitorKeys?, enter?, leave? })`; instance exposes `current()`, `parents()` (COPY), `skip()`, `break()`.
**Data Shape:** nodes recognized as `x !== null && typeof x === "object" && typeof x.type === "string"`; child keys come from the supplied visitorKeys map, falling back to `eslint-visitor-keys.getKeys(node)` for unknown types.

### Decisive source
```js
_traverse(node, parent) {
  if (!isNode(node)) return;
  this._current = node; this._skipped = false;
  this._enter(node, parent);
  if (!this._skipped && !this._broken) {
    const keys = getVisitorKeys(this._visitorKeys, node);
    if (keys.length >= 1) {
      this._parents.push(node);
      for (let i = 0; i < keys.length && !this._broken; ++i) {
        const child = node[keys[i]];
        if (Array.isArray(child))
          for (let j = 0; j < child.length && !this._broken; ++j)
            this._traverse(child[j], node);
        else this._traverse(child, node);
      }
      this._parents.pop();
    }
  }
  if (!this._broken) this._leave(node, parent);   // leave STILL runs after break of children
  this._current = parent;
}
// unknown type ⇒ vk.getKeys estimate + debug log — never throws
```

**Flow:** enter → unless skipped/broken push to parents and recurse key-order (arrays in order) → pop → leave, all loops checking `_broken`.
**Invariant:** `break()` stops CHILD traversal but the current node's `leave` still fires once (`if (!this._broken) this._leave`) — semantics differ subtly from skipping everything. `skip()` skips only descendants of the current node. Unknown node types DEGRADE (estimated keys + log) rather than throw, because plugins inject foreign ASTs. `parents()` returns a slice copy so callers can't corrupt the traversal stack. This is the traverser RuleTester itself uses for AST-immutability snapshots — it must stay dependency-light.
**Probe:** `tests/lib/shared/traverser.js` (:15–61 key coverage incl. leadingComments/trailingComments exclusion via visitor keys; :62–109 custom visitorKeys reaching experimentalDecorators).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "shared Traverser traverse getVisitorKeys isNode", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.shared.traverser.Traverser.traverse" });
```

## Verdict
Adopt for any plugin-facing walker; keep the unknown-type degradation and the leave-after-break rule exactly. Omit the class-method state machine if your host already has an equivalent — but re-verify ITS break/leave semantics first; most get it wrong.
