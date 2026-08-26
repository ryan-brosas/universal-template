<!-- capsule-v2 -->
# Rule execution engine — how do you instantiate rule listeners, enforce report metadata, and traverse the AST with esquery selectors?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does one verify pass turn N configured rules into ordered node callbacks, and what must a porter not break?

## runRules listener assembly
**Path/Symbol:** `lib/linter/linter.js:runRules` (:523–689) + `createRuleListeners` (:485–502).
**Signature:** `runRules(sourceCode, configuredRules, ruleMapper, language, languageOptions, settings, filename, applyDefaultOptions, cwd, physicalFilename, ruleFilter, stats, slots, report): FileReport`.
**Data Shape:** per rule a `FileContext` extension carries `{ id: ruleId, options: getRuleOptions(...) }`; the shared base context is frozen once and inherited (perf), not copied per rule; disabled rules (severity 0) are never loaded.

### Decisive source
```js
const ruleContext = fileContext.extend({
  id: ruleId,
  options: getRuleOptions(configuredRules[ruleId], applyDefaultOptions ? rule.meta?.defaultOptions : void 0),
  report(...args) {
    const problem = report.addRuleMessage(ruleId, severity, ...args);
    if (problem.fix && !(rule.meta && rule.meta.fixable)) {
      throw new Error('Fixable rules must set the `meta.fixable` property to "code" or "whitespace".');
    }
    // ... hasSuggestions enforcement mirrors this for suggestions
  },
});
// every listener is wrapped so thrown errors carry err.ruleId:
visitor.add(selector, addRuleErrorHandler(ruleListener));
```

**Flow:** skip severity-0 / filtered rules → resolve via `ruleMapper` (missing ⇒ reported error, not throw) → build context → `create()` returns `{ selector: fn }` listeners → wrap each in error handler + optional timing → register on a `SourceCodeVisitor` keyed by esquery selector.
**Invariant:** `meta.fixable`/`meta.hasSuggestions` are validated at *report time* (a rule that reports a fix without declaring fixable throws mid-run); listener errors are annotated with `err.ruleId` so the traversal failure names the culprit; a `create()` returning non-object throws.
**Probe:** `tests/lib/rule-tester/rule-tester.js` + `tests/lib/linter/linter.js` (fixable/suggestions metadata errors, error attribution).

## Selector traversal
**Path/Symbol:** `lib/linter/source-code-traverser.js:ESQueryHelper` (:46–221) + `SourceCodeTraverser.traverseSync` (:269–330).
**Signature:** `traverseSync(sourceCode, visitor, { steps }): void`; steps come from `sourceCode.traverse()` (`kind:1 visit enter/exit`, `kind:2 call`).
**Data Shape:** selectors parsed once into `enterSelectorsByNodeType` / `exitSelectorsByNodeType` Maps plus any-type arrays, all pre-sorted by esquery specificity; per-node matching walks both lists in specificity order (merge of two sorted lists).

### Decisive source
```js
if (step.phase === 1) {
  esquery.calculateSelectors(step.target, currentAncestry, false)
    .forEach(selector => visitor.callSync(selector, ...(step.args ?? [step.target])));
  currentAncestry.unshift(step.target);          // ancestry BEFORE exit-phase matching
} else {
  currentAncestry.shift();
  esquery.calculateSelectors(step.target, currentAncestry, true).forEach(/* call */);
}
```

**Flow:** enter phase matches+calls selectors then pushes node onto ancestry; exit pops first, then matches — so ancestor-relative selectors (`X > Y`, `X Y`) see the correct ancestry on both phases; traversal errors attach `err.currentNode`.
**Invariant:** specificity order decides listener call order for co-matched selectors (rules relying on ordering break if you sort differently); the ancestry push happens *after* enter-calls and the shift *before* exit-calls — reversing either breaks parent/child selector semantics. Traverser instances are cached per-Language (`WeakMap`).
**Probe:** `tests/lib/linter/source-code-traverser.js` (specificity order, enter/exit ancestry).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "runRules SourceCodeTraverser traverseSync", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.source-code-traverser.SourceCodeTraverser.traverseSync" });
```

## Verdict
Adopt the frozen-shared-context + selector-registry execution model, report-time metadata enforcement, and the enter/exit ancestry discipline; adapt the timing/stats hooks and ruleMapper to host rule storage; omit ESLint's processor/language plugin abstractions if porting only the JS core loop.
