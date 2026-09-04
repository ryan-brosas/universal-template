<!-- capsule-v2 -->
# Directive-prologue & directive-comment recognition — how do you tell a "use strict" or an eslint comment from ordinary string expressions?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** What exact predicates decide that an ExpressionStatement is a directive, and that a comment is an eslint directive comment?

## ast-utils directive predicates
**Path/Symbol:** `lib/rules/utils/ast-utils.js:isTopLevelExpressionStatement(node)` (:1303–1316), `isDirective(node)` (:1321–1328), `isStartOfExpressionStatement(node)` (:1333–1346), `isDirectiveComment(node)` (:1685–1691), `ESLINT_DIRECTIVE_PATTERN` (:47).
**Signature:** `isDirectiveComment(node: Line|Block): boolean`.
**Data Shape:** Line comments must start `eslint-`; Block comments must match `/^(?:eslint[- ]|(?:globals?|exported) )/` on trimmed value (covers `eslint`, `eslint-…`, `eslint …`, `global(s) …`, `exported …`, plus jshint/jslint/istanbul/jscs in COMMENTS_IGNORE_PATTERN).

### Decisive source
```js
function isTopLevelExpressionStatement(node) {
  if (node.type !== "ExpressionStatement") return false;
  const parent = node.parent;
  return parent.type === "Program" || parent.type === "TSModuleBlock" ||
         (parent.type === "BlockStatement" && isFunction(parent.parent));
}
function isDirective(node) {
  return node.type === "ExpressionStatement" && typeof node.directive === "string";
}
function isStartOfExpressionStatement(node) {   // walk parents sharing range[0]
  const start = node.range[0];
  let ancestor = node;
  while ((ancestor = ancestor.parent) && ancestor.range[0] === start) {
    if (ancestor.type === "ExpressionStatement") return true;
  }
  return false;
}
```

**Flow:** prologue position = Program / TSModuleBlock / directly-inside-function body; parser supplies `.directive` for actual directives; the shared-start walk handles nested expression parenthesization (`( "use strict" )`) by climbing ancestors whose range begins at the same offset.
**Invariant:** "directive" is POSITION + grammar (first sibling or after another directive — per JSDoc), not merely string-literal-ness; a `"use strict"` mid-function is NOT one. The range-shared ancestor climb is the trick porters miss: without it, wrapped/parenthesized directives lose their prologue status. Comment recognition is deliberately prefix-based (not exact-match) so plugin-style `eslint-foo` directives inherit detection.
**Probe:** `tests/lib/rules/utils/ast-utils.js` (:363 isDirectiveComment describe; 59 describe blocks total covering getStaticStringValue/getStaticPropertyName twins); directive helpers exercised via no-inline-comments/directive consumers (`tests/lib/rules/no-inline-comments.js:36+`); consumer pinning in `lib/linter/apply-disable-directives.js` comment scanning.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "isDirectiveComment isTopLevelExpressionStatement isDirective isStartOfExpressionStatement", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rules.utils.ast_utils.isDirectiveComment" });
```

## Verdict
Adopt the position+range-climb definition of directive prologues for any tool honoring "use strict"-style headers; adapt the comment-prefix table.
