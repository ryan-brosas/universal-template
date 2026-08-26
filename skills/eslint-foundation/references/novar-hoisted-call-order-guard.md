<!-- capsule-v2 -->
# No-var hoisted-function call-order guard — when may the var→let autofix rewrite a `var` that a hoisted FunctionDeclaration reads?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (#21213); Codebase Memory project `mnt-hdd-utopia-inspo-frameworks-eslint` (path-slugged twin; stuck short-name `eslint` serves the pre-drift graph). **Question:** A `var` read only *inside* a hoisted function passes every text-order guard — under what exact condition does converting it to `let` still break the program, and how is that condition detected statically?

## hasUnsafeHoistedFunctionReference
**Path/Symbol:** `lib/rules/no-var.js:hasUnsafeHoistedFunctionReference` (:231–272), wired as the seventh `canFix` veto at :418 between `hasReferenceBeforeDeclaration` and `isShadowedByCatchParameter`.
**Signature:** `hasUnsafeHoistedFunctionReference(variable: Variable) -> boolean`.
**Data Shape:** input is one `Variable` from `sourceCode.getDeclaredVariables(node)`; `variable.defs[0].node` is the declaring node (`declarationStart = range[0]`); each reference carries `{init, identifier, from}`; the walk hops scope chains (`from.variableScope`, `.upper.variableScope`) and resolves each enclosing function's own name binding through `currentScope.upper.set.get(funcName)`.

### Decisive source
```js
let currentScope = reference.from.variableScope;
while (currentScope !== variable.scope) {
    if (currentScope.block.type === "FunctionDeclaration" && currentScope.block.id) {
        const funcName = currentScope.block.id.name;
        const funcVariable = currentScope.upper.set.get(funcName);
        for (const funcRef of funcVariable.references) {
            const refId = funcRef.identifier;
            if (refId.parent.type === "CallExpression" &&
                refId.parent.callee === refId &&
                refId.range[0] < declarationStart) {
                return true;   // hoisted function CAN run before the var executes
            }
        }
    }
    currentScope = currentScope.upper.variableScope;
}
```

**Flow:** for each non-init reference AT-or-after the declaration start, climb the scope chain toward the variable's own scope; every intermediate FunctionDeclaration scope is a potential hoisted reader; resolve that function's Variable in its parent scope's set and scan ITS references for callee-position calls that begin before the declaration. Any hit vetoes the fix (`canFix` returns false → `report()`'s `fix()` returns null → message emitted with NO `output`).
**Invariant:** the hazard is **call order, not textual reference order**: `var a = 1; f(); function f(){ console.log(a); }` is safe (function defined-and-read after decl runs later), but `f(); var a = 1; function f(){ console.log(a); }` becomes a TDZ ReferenceError once converted — the ONLY static signal distinguishing them is a callee-position CallExpression of the hoisted function preceding `declarationStart`. Three porting traps: (1) the function-name lookup goes through `currentScope.upper.set` (the binding lives one scope ABOVE the function's body scope); (2) `reference.init` refs are skipped consistently with the sibling guards — the declarator's own identifier is not a "use"; (3) `canFix` judges the WHOLE declaration all-or-nothing, so `var b = foo(), a = 1` blocks both declarators even though only `a` is captured (multi-declarator safety is coarse by design; independent statements are judged independently, which is why `foo(); var a = 1; var b = 2;` still fixes `b`). This guard is unreachable-by-textual-order alone: `hasReferenceBeforeDeclaration` already covers direct pre-decl reads, and `hasReferenceInTDZ` only scans initializer ranges — hoisted bodies live outside both.

**Probe:** `tests/lib/rules/no-var.js:562-587` — six cases pinning the matrix: call-before-decl ⇒ no output (:562), call-after-decl ⇒ fixed to let (:565), two-level transitive chain `bar→inner→a` ⇒ no output (:568), capture via earlier declarator's initializer `var b = foo()` ⇒ no output (:571), selective per-statement fixing (:574–582), nested-block variant with duplicate function id (:583). Behaviorally executed (harness: espree 10.4.0 + eslint-scope 8.4.0 driving the rule file from disk): RED at `dc1e7a84` converted all four unsafe cases to `let`; GREEN at `c27bc92` suppresses the fix (null) on all four while preserving B/E/F. Adversarial beyond upstream: `f(); var a = 1; function f(){ a = 2; }` (write-only body, called before decl) is ALSO guarded — the guard fires on invocation position regardless of what the body does with the variable.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-eslint", name_pattern: "hasUnsafeHoistedFunctionReference", limit: 10 });
// resolves: ...no-var.hasUnsafeHoistedFunctionReference Function lib/rules/no-var.js 231-272
```

## Verdict
Adopt the guard as a mandatory checklist item for any hoisting-semantics-sensitive rewrite fixer: before rewriting a declaration keyword, enumerate functions that close over the binding AND can execute before the declaration statement. Adapt the scope-manager API shape (`variableScope`/`upper.set`) to the host analyzer; keep the callee-position + range-comparison definition of "called earlier". Omit nothing. Coverage caveat: probes executed via extracted-tree behavioral harness, not the repo mocha suite (inspo clone has no installed toolchain).
