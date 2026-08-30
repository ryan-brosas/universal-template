<!-- capsule-v2 -->
# ESM identifier walker — how does the AST walker decide which identifiers are real references (to rewrite) vs. bindings to skip, so hoisting/rewrite transforms don't corrupt scopes?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How does `esmWalker` (the acorn-AST twin of `@vue/compiler-core`'s walker) track scope and classify identifiers so a porter can safely rewrite imports/dynamic-imports/import.meta without breaking shadowing?

## Scope-aware identifier classification
**Path/Symbol:** `packages/mocker/src/node/esmWalker.ts:esmWalker` (:64–280), `isRefIdentifier` (:282–353), `findParentScope` (:373–378), `getArbitraryModuleIdentifier` (:394–396).
**Signature:** `esmWalker(root, { onIdentifier, onImportMeta, onDynamicImport, onCallExpression }) => void`.
**Data Shape:** maintains a `parentStack` (unshift/shift on enter/leave, skipping `if`-alternate nesting), a `varKindStack` (for `var` vs block scoping), and a `scopeMap: WeakMap<Node, Set<string>>` recording every declared name per scope. Identifiers that are genuine references are COLLECTED during the DFS walk and re-emitted in BFS order afterwards (so hoisted declarations are seen first).

### Decisive source
```ts
// enter: record scope bindings; collect reference identifiers for BFS re-emit
if (node.type === 'Identifier') {
  if (!isInScope(node.name, parentStack) && isRefIdentifier(node, parent!, parentStack)) {
    identifiers.push([node, parentStack.slice(0)])   // defer; emit in BFS after walk
  }
} else if (node.type === 'ClassDeclaration' && node.id) {
  const parentScope = findParentScope(parentStack); if (parentScope) setScope(parentScope, node.id.name)
} else if (isFunctionNode(node)) {
  if (node.type === 'FunctionDeclaration') { const ps = findParentScope(parentStack); if (ps) setScope(ps, node.id!.name) }
  node.params.forEach(p => { /* handlePattern adds params to scope so they aren't rewritten */ })
}
// leave: untrack parentStack / varKindStack
// BFS emit: re-check isInScope, then classify the reference
identifiers.forEach(([node, stack]) => {
  if (!isInScope(node.name, stack)) {
    const parent = stack[0]
    const hasBindingShortcut = isStaticProperty(parent) && parent.shorthand
      && (!isNodeInPattern(parent) || isInDestructuringAssignment(parent, parentStack))
    const classDeclaration = parent.type === 'ClassDeclaration' && node === parent.superClass
    const classExpression = parent.type === 'ClassExpression' && node === parent.id
    onIdentifier?.(node, { hasBindingShortcut, classDeclaration, classExpression }, stack)
  }
})
```

**Flow:** the walker descends the AST tracking the parent stack and each scope's declared names (`setScope` on variable declarators, function params, class/function declaration names, catch params, destructuring patterns). `isRefIdentifier` filters out non-references (declaration ids, function ids/params, class method names, property keys, member-expression properties, export specifiers, `arguments`, destructuring-pattern targets). Reference identifiers are buffered, then re-emitted in BFS order so a hoisted `import`/declaration is in scope before its uses are rewritten.
**Invariant:** the BFS re-emit is the load-bearing trick — DFS would rewrite a use before the hoisted binding that shadows it is recorded. Scope is tracked per-node in a WeakMap keyed by scope node, and `var`-kind variables climb to the nearest FUNCTION scope (`findParentScope(stack, isVar=true)`) while `let`/`const` stop at the nearest block. `hasBindingShortcut` flags `{ foo }` shorthand so the caller knows to rewrite it as `{ foo: __x__.foo }`. The `isNodeInPatternWeakSet` marks object-pattern properties so `isRefIdentifier` treats them as bindings, not references.
**Probe:** exercised by every automock/hoist transform under `packages/mocker/src/node/`; `test/unit/test/browserAutomocker.test.ts` inline snapshots pin that shadowed identifiers are NOT rewritten (the walker's scope correctness is what makes those snapshots stable). `esmWalker.ts:16` is a type-only `export type *` line (parse_partial, non-blocking).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "esmWalker isRefIdentifier", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the DFS-collect/BFS-emit identifier walker with per-scope WeakMap scope tracking, the `isRefIdentifier` exclusion set, and the `hasBindingShortcut`/`classDeclaration`/`classExpression` classification — a portable safe-rewrite kernel for import/hoist transforms. Adapt the visitor callbacks to your transform's needs; the walker itself is host-agnostic. Omit `getArbitraryModuleIdentifier` (a trivial name/raw extractor) unless you need the literal-vs-identifier distinction.
