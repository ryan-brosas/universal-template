<!-- capsule-v2 -->
# RuleTester config assembly — how do tester-level options, per-case properties, and rule options layer into one flat config per case?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How exactly does runRuleForItem turn `{code, options, filename, ...extras}` into configs, and why is the default plugin's rules proxy preserved?

## baseConfig + item-as-config
**Path/Symbol:** `lib/rule-tester/rule-tester.js:run` baseConfig construction (:1050–1094), `RuleTesterParameters` stripping (:1167–1175), itemConfig push + options application (:1179–1185), schema fetch + ajv validation ladder (:1188–1290).
**Signature:** `configs.push(itemConfig)` then `configs.push({rules: {[ruleId]: [1, ...options]}})`.
**Data Shape:** `testerConfig = [sharedDefaultConfig, testerConfig, {rules: {"rule-tester/validate-ast": "error"}}]`; `RuleTesterParameters = ["name","code","filename","options","before","after","errors","output","only"]`.

### Decisive source
```js
"@" : {
  parsers: { ...defaultConfig[0].plugins["@"].parsers },   // COPY parsers…
  rules: defaultConfig[0]["@"].rules,                      // …SHARE the lazy rules proxy
  languages: defaultConfig[0]["@"].languages,
},
// comment-pinned rationale: "The rules key … is a proxy to lazy-load just the rules
//  that are needed. So, don't create a new object here."
```

**Flow:** every non-parameter property of the test case becomes a CONFIG ENTRY (so cases can set `languageOptions`, `settings`, plugins per-case) → the rule is always enabled at severity 1 with case options spread after → schema fetched via Config.getRuleOptionsSchema, ajv validateSchema THEN compile (separate steps because some errors only surface at compile) → normalizeSync/getConfig wrapped to rebrand failures as "ESLint configuration in rule-tester is invalid".
**Invariant:** parser objects are copied fresh per `run()` call so wrapParser's start/end getters never stack across runs, while the rules PROXY is shared for cold-start performance — copy-vs-share per surface is deliberate. Options enter as `[1, ...options]`: severity first, user options after. before/after hooks run around each case with assert on typeof.
**Probe:** `tests/lib/rule-tester/rule-tester.js` (:2119 schema-violation prevention; per-case languageOptions/plugin usage throughout; ajv compile-step errors).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "RuleTester baseConfig RuleTesterParameters itemConfig", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rule_tester.rule_tester.RuleTester.run" });
```

## Verdict
Adopt case-properties-as-config for declarative harnesses; respect the copy-parsers/share-proxy split when rebasing onto newer flat-config internals.
