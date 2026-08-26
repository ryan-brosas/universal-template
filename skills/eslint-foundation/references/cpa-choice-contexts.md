<!-- capsule-v2 -->
# CPA choice-context algebra — how do `&&`/`||`/`??`, if/else, and optional chaining share one fork-merge machine?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you model every boolean-ish fork (logical ops, ternaries, if statements, `?.`) with one context type and get short-circuit edges right?

## ChoiceContext + makeLogicalRight
**Path/Symbol:** `lib/linter/code-path-analysis/code-path-state.js:ChoiceContext` (:121–178), `CodePathState.pushChoiceContext/popChoiceContext` (:1077–1181), `makeLogicalRight` (:1190–1285), `makeIfConsequent/makeIfAlternate` (:1291–1330).
**Signature:** `pushChoiceContext(kind, isForkingAsResult)` where kind ∈ `"&&"|"||"|"??"|"test"|"loop"`; popped context carries `trueForkContext/falseForkContext/nullishForkContext` + `processed` flag.
**Data Shape:** three per-choice accumulators; `isForkingAsResult=true` marks a logical expression nested as the *test* of another choice (`a || b || c`: left `a||b` forks as result of `|| c`; a terminal `a || b` does not fork).

### Decisive source
```js
// entering the right operand — two regimes:
if (currentChoiceContext.processed) {          // child choice results already flowed in
  let prevForkContext;
  switch (kind) {
    case "&&": prevForkContext = trueForkContext; break;    // only truthy reaches right
    case "||": prevForkContext = falseForkContext; break;   // only falsy reaches right
    case "??": prevForkContext = nullishForkContext; break; // both true/false short-circuit
  }
  forkContext.replaceHead(prevForkContext.makeNext(0, -1));
  prevForkContext.clear(); currentChoiceContext.processed = false;   // reset for pop
} else {                                       // terminal logical: seed short-circuit paths
  switch (kind) {
    case "&&": falseForkContext.add(head); nullishForkContext.add(head); break;
    case "||": trueForkContext.add(head); break;
    case "??": trueForkContext.add(head); falseForkContext.add(head); break;
  }
  forkContext.replaceHead(forkContext.makeNext(-1, -1)); // new segment for the right operand
}
```

**Flow:** pop merges `trueFork ∪ falseFork` into one combined head unless `isForkingAsResult` (then the three accumulators are lifted into the *parent* choice context and it's marked `processed`). If/ternary reuse the same context with kind `"test"`: `popChoiceContext` writes head into `trueForkContext` when consequent ran last or `falseForkContext` when alternate did. Optional chaining is a synthetic `??`: `ChainExpression` pushes a counting `ChainContext`, each `optional:true` Call/Member node pushes a `"??"` choice, `makeOptionalRight` reuses `makeLogicalRight`, and `popChainContext` pops exactly `choiceContextCount` choices.
**Invariant:** `??` needs its own third accumulator because BOTH operands' outcomes can short-circuit; the `processed` flag must be cleared after consumption or `popChoiceContext` double-adds segments; `makeOptionalNode`/`makeOptionalRight` are no-ops outside a chain (`if (this.chainContext)` guard) — bare `a?.b` at statement level never creates orphan contexts.
**Probe:** `tests/lib/linter/code-path-analysis/code-path-analyzer.js` (event suites :255–794) + `tests/lib/rules/no-fallthrough.js`-style consumers via rule tests; direct: `tests/lib/linter/code-path-analysis/code-path.js` traverse cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "pushChoiceContext makeLogicalRight popChainContext nullishForkContext", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.code-path-analysis.code-path-state.CodePathState.makeLogicalRight" });
```

## Verdict
Adopt the single ChoiceContext with kind discriminator + result-lifting between nested choices + processed-flag lifecycle; adapt operator set to your language's short-circuit forms; omit ChainExpression emulation if your AST resolves optionality differently.
