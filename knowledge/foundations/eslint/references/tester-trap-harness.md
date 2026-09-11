<!-- capsule-v2 -->
# RuleTester parser-wrapping & forbidden-method interception — how does a test harness make illegal AST access and legacy API calls fail loudly?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** Beyond the wrapper-rule/AST-sentinel pair (rules-and-tester capsule), which mechanical traps catch start/end access, legacy SourceCode methods, and unparseable autofixes?

## Parser wrapping via finalizeConfig override
**Path/Symbol:** `lib/rule-tester/rule-tester.js:wrapParser(parser)` (:279–303), `defineStartEndAsError(objName, node)` (:235–256), `defineStartEndAsErrorInTree(ast, visitorKeys)` (:264–277), `runRuleForItem` finalizeConfig override (:1146).
**Data Shape:** wrapped parser keeps the original under `Symbol.for("eslint.RuleTester.parser")`; `start`/`end` become non-enumerable getter properties that THROW with "Use node.range[0] instead of node.start".
**Flow:** per test case the FlatConfigArray's `finalizeConfig` is overridden to wrap the parser AFTER normal finalization — ONLY when `calculatedConfig.language === jslang` (foreign-language plugins keep their own parsers).

## Forbidden SourceCode prototype methods
**Path/Symbol:** `throwForbiddenMethodError(methodName, prototype)` (:309–327) over `forbiddenMethods = ["applyInlineConfig","applyLanguageOptions","finalize"]` (:147–151) + `forbiddenMethodCalls` WeakSet-per-method map; patched around `linter.verify` in try/finally (:1292–1329).
**Decisive source:**
```js
return function (...args) {
  const called = forbiddenMethodCalls.get(methodName);
  if (!called.has(this)) { called.add(this); return original.apply(this, args); } // FIRST call allowed
  throw new Error(`\`SourceCode#${methodName}()\` cannot be called inside a rule.`);
};
```
**Invariant:** ONE call per method per SourceCode instance is permitted (the linter's own internal invocation), subsequent calls throw — a WeakSet keyed on `this` distinguishes instances without leaking. Prototype patching is global-mutation and MUST be restored in `finally` or one failed test poisons every later one.

## Fatal-in-autofix re-verification
**Path/Symbol:** runRuleForItem fix check (:1319–1337) + fatal-in-fix guard (:1325–1334) + suggestion-output re-verify inside testInvalidTemplate (:1816–1852).
**Flow:** if any message has `.fix`: applyFixes → RE-LINT output → assert no fatal ("A fatal parsing error occurred in autofix" + output echoed). Every expected suggestion is applied INDIVIDUALLY to item.code and re-linted too.
**Invariant:** parse-validity of fixed code is asserted by re-linting, never trusted; suggestions must differ from source (`notStrictEqual(expected.output, item.code)`), making no-op suggestions a test failure.

**Probe:** `tests/lib/rule-tester/rule-tester.js` (start/end-throw matrix :211/:2279/:2364 "Use node.range[0] instead of node.start"; forbidden-method errors :5268+; fatal-in-fix assertions :1532/:1550; suggestion re-lint inside testInvalidTemplate :1816–1852).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "wrapParser defineStartEndAsError throwForbiddenMethodError", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rule_tester.rule_tester.wrapParser" });
```

## Verdict
Adopt all three traps for any rule/plugin harness: getter-throws for deprecated fields, first-call-allowed WeakSet interception for internals, and re-lint-the-patch verification. Restore global patches in finally — non-negotiable.
