<!-- capsule-v2 -->
# Message-template node tree — How is a recursive template tree validated so bad branches cannot slip through?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** which node kinds exist and what does each predicate actually pin down before rendering?

## `IMessageTemplateNodes` recursive predicate family
**Path/Symbol:** `core/public-methods/models/messages/MessageTemplate/IMessageTemplateNodes.js` (whole file, lines 7–58; graph cluster fan-in: isGroupNode/isVarNode/isTextNode 2 each).
**Signature:** `isAnyNode(data): boolean` — union dispatcher; predicates: `isTextNode`, `isVarNode`, `isPrimitiveNode`, `isIfNode`, `isVariantNode`, `isVariantsNode`, `isGroupNode`, `isPrimitiveGroupNode`.
**Data Shape:** node kinds — text `{type:'text', value:string}`; var `{type:'var', name:string}`; if `{type:'if', if:primitive-group, then:group, else:group}`; variants `{type:'variants', variants:[variant…] nonempty}`; variant `{type:'variant', child:any-node}`; group `{type:'group', children:[any-node…]}`.

### Decisive source
```js
function isIfNode(data) {
    return Boolean(arg && arg.type === 'if' &&
        isPrimitiveGroupNode(arg.if) &&     // condition branch: text/var ONLY
        isGroupNode(arg.then) && isGroupNode(arg.else));
}
function isVariantsNode(data) {
    return Boolean(arg && arg.type === 'variants' && Array.isArray(arg.variants) &&
                   arg.variants.length > 0 && arg.variants.every(isVariantNode));
}
function isGroupNode(data) {
    return Boolean(arg && arg.type === 'group' && Array.isArray(arg.children) && arg.children.every(isAnyNode));
}
function isPrimitiveGroupNode(data) {
    return Boolean(arg && arg.type === 'group' && Array.isArray(arg.children) && arg.children.every(isPrimitiveNode));
}
function isAnyNode(data) { return isTextNode(data) || isVarNode(data) || isIfNode(data) || isVariantsNode(data) || isGroupNode(data); }
```

**Flow:** leaf kinds validated structurally (text/var) -> containers recurse via `every(isAnyNode)` / `every(isVariantNode)` -> mutual recursion isAnyNode ↔ isGroupNode/isVariantsNode terminates because children arrays shrink per level -> if-nodes tighten the condition slot to a primitive-only group.
**Invariant:** a valid tree has no empty variants list, every variant wraps exactly one child, and the `if` condition can only contain text/var nodes — conditional logic itself is never conditional.
**Probe:** `node -e "const N=require('<root>/core/public-methods/models/messages/MessageTemplate/IMessageTemplateNodes.js').IMessageTemplateNodes; console.log(N.isAnyNode({type:'group',children:[{type:'text',value:'hi'},{type:'var',name:'a'}]}), N.isAnyNode({type:'group',children:[]}))" → expect true false`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", qn_pattern: ".*IMessageTemplateNodes.*", format: "json" });
```

## Verdict
Adopt the discriminated-by-`type` recursive validator as the cheap alternative to a parser when templates are data, not code. Adapt node-kind vocabulary to your renderer. Omit nothing behavioral — the module is self-contained and portable; keep citations-only (proprietary).
