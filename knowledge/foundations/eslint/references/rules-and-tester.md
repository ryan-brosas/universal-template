<!-- capsule-v2 -->
# RuleTester harness — how do you run a rule against valid/invalid cases while asserting AST immutability, fix validity, and exact message contracts?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does the tester turn `{valid, invalid}` cases into a self-policing rule execution harness?

## Wrapper rule + AST-immutability sentinel
**Path/Symbol:** `lib/rule-tester/rule-tester.js:RuleTester.run → runRuleForItem` (:1040–1347; wrapper :1073–1088, validate-ast plugin :1220–1240, assertASTDidntChange :1356–1360).
**Signature:** `new RuleTester(testerConfig?).run(ruleName, rule, { valid: (ValidTestCase|string)[], invalid: InvalidTestCase[] }): void`.
**Data Shape:** rule registered under `"rule-to-test/<name>"`; tester config layers as `[sharedDefaultConfig, testerConfig, { rules: { "rule-tester/validate-ast": "error" } }]`; each case's extra properties become a pushed config entry; options applied via `rules: { [ruleId]: [1, ...options] }`.

### Decisive source
```js
"rule-to-test": { rules: { [ruleName]: Object.assign({}, rule, {
  create(context) {
    freezeDeeply(context.options);     // cases may not mutate their own options
    freezeDeeply(context.settings);
    freezeDeeply(context.parserOptions);
    return rule.create(context);
  },
}) } },
// separate always-on internal rule snapshots the AST:
Program(node)      { beforeAST = cloneDeeplyExcludesParent(node); },
"Program:exit"(node) { afterAST = node; }
// then: if (!equal(beforeAST, afterAST)) assert.fail("Rule should not modify AST.");
```

**Flow:** per case — build a fresh `FlatConfigArray` (baseConfig carries the wrapped rule) → override `finalizeConfig` to wrap the parser (catches illegal start/end access on tokens/locations) → forbid legacy SourceCode methods by prototype patching inside try/finally → `linter.verify` → assert no fatal parse error.
**Invariant:** rules must treat context data and the AST as read-only — both are enforced mechanically, not by convention. Each test case gets a *fresh* parser wrapper object (wrapping a shared one would stack wrappers across cases).
**Probe:** `tests/lib/rule-tester/rule-tester.js` (AST mutation failure, frozen-options failure, forbidden-method errors).

## Assertion ladder + autofix re-verification
**Path/Symbol:** `lib/rule-tester/rule-tester.js:testInvalidTemplate` (:1415–1900+) + autofix check in `runRuleForItem` (:1319–1337).
**Data Shape:** `errors` may be a count or an array of string | RegExp | `{message|messageId, data?, line?, column?, endLine?, endColumn?, suggestions?}`; `assertionOptions` (`requireMessage`, `requireLocation`, `requireData`) tighten laxity for monorepo rule suites.

### Decisive source
```js
if (messages.some(m => m.fix)) {
  output = SourceCodeFixer.applyFixes(code, messages).output;
  const errorMessageInFix = linter.verify(output, configs, filename).find(m => m.fatal);
  assert(!errorMessageInFix, ["A fatal parsing error occurred in autofix.", ...].join("\n"));
}
```

**Flow:** invalid cases assert error count, then per-index message match (RegExp supported), messageId validity against `meta.messages`, unsubstituted-placeholder detection, location deep-equal only over keys the test specifies, suggestion uniqueness/desc/messageId/data contracts → any produced autofix output is *re-linted* to prove it still parses.
**Invariant:** a fix that produces unparseable code fails the test even though the original messages matched — fix correctness is verified by re-linting, not by trusting `output`. Suggestions must be unique per message and every placeholder filled via `data`.
**Probe:** `tests/lib/rule-tester/rule-tester.js` (fatal-in-autofix assertion, suggestion dedup errors).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "RuleTester runRuleForItem assertASTDidntChange testInvalidTemplate", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rule-tester.rule-tester.RuleTester.run" });
```

## Verdict
Adopt the wrapper-rule freezing, AST-snapshot internal rule, prototype-guarded SourceCode methods, and re-lint-the-fix assertion; adapt the assertion ladder strictness knobs to host test conventions; omit Mocha-specific describe/it plumbing (the default handlers just execute synchronously).
