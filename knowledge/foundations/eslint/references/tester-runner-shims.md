<!-- capsule-v2 -->
# RuleTester framework shims & assertion strictness — how does the harness stay runner-agnostic while letting suites tighten message contracts?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do describe/it/only resolve across Mocha, Vitest, and no-runner contexts, and what do `assertionOptions` tighten?

## Runner resolution + default handlers
**Path/Symbol:** `lib/rule-tester/rule-tester.js:RuleTester` static describe/it/itOnly accessors (:954–1018) over symbol slots `DESCRIBE/IT/IT_ONLY` (:853–855), `describeDefaultHandler` (:883), `itDefaultHandler` (:865), `RuleTester.only(item)` (:978).
**Signature:** static getters: symbol override → global `describe`/`it` → default (synchronous execution).
**Data Shape:** itDefaultHandler appends `util.inspect(err.actual) err.operator util.inspect(err.expected)` to AssertionError messages for readable failures without a real runner.

### Decisive source
```js
static get describe() {
  return this[DESCRIBE] || (typeof describe === "function" ? describe : describeDefaultHandler);
}
static get itOnly() {
  if (typeof this[IT_ONLY] === "function") return this[IT_ONLY];
  if (typeof this[IT] === "function" && typeof this[IT].only === "function")
    return Function.bind.call(this[IT].only, this[IT]);
  ...
  throw new Error("Set `RuleTester.itOnly` to use `only` with a custom test framework.\n" ...);
}
```

**Flow:** fresh accessor evaluation per run (mocha --watch swaps globals between passes — comment-pinned) → valid/invalid arrays become nested describes, created CONDITIONALLY so empty suites don't crash vitest; test names are `sanitize(item.name || item.code)` with control chars escaped `\u00xx`.
**Invariant:** `only` support is probed, never assumed — three distinct error messages guide custom-framework users. Default handlers make RuleTester runnable inside plain node scripts (every test executes immediately).

## assertionOptions strictness knobs
**Path/Symbol:** `assertErrorsProperty(errors, ruleName, {requireMessage, requireLocation})` (:394) + requireData branches in testInvalidTemplate (:1516–1545 error-side message/messageId matching; :1575–1576 + :1770–1813 suggestion-side requireData).
**Flow:** requireMessage:"messageId" forbids string/RegExp error entries AND message+messageId mixing; requireLocation demands all four location keys present on both sides; requireData:true|"error"|"suggestion" rejects messageId assertions whose template has placeholders but the case supplied no data.
**Invariant:** lax-by-default, tighten-per-suite — designed for monorepos owning hundreds of rules to enforce uniform assertion quality without breaking third-party usage.
**Probe:** `tests/lib/rule-tester/rule-tester.js` (:2861–2878 requireMessage:"messageId"; :2881 requireData-no-messageIds edge; requireMessage suite :5443+, requireLocation suite :5885+, requireData suite :6220+).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "RuleTester itOnly itDefaultHandler assertErrorsProperty assertionOptions", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rule_tester.rule_tester.RuleTester.only" });
```

## Verdict
Adopt the accessor-chain runner resolution and conditional suite creation for any declarative harness; adopt assertionOptions-style tightening when one harness serves many teams.
