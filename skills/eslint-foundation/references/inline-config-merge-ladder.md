<!-- capsule-v2 -->
# Inline-config merge ladder — how does `/* eslint rule: [severity] */` splice severity while KEEPING file-level options (and when is revalidation skipped)?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do inline configuration comments override severities without clobbering configured options, and how are duplicate/unused/invalid inline configs handled?

## #flatVerifyWithoutProcessors inline phase
**Path/Symbol:** `lib/linter/linter.js:#flatVerifyWithoutProcessors` (:979–1315) — inline merge block (:1046–1243), `addProblemIfSameSeverityAndOptions` (:159–215), directive collection `getDirectiveCommentsForFlatConfig` (:294–324) + `createDisableDirectives` (:231–283), final merge + run (:1245–1314).
**Signature:** merged rules = `{...config.rules, ...mergedInlineConfig.rules}`; each inline entry passes through the ladder below before merging.
**Data Shape:** `options.warnInlineConfig` (set when config says `noInlineConfig`) turns the whole phase into warning emission; `reportUnusedInlineConfigs` severity gates redundancy reporting.

### Decisive source
```js
// severity-only inline + rule already configured ⇒ keep config options:
if (ruleOptions.length === 1 && config.rules && Object.hasOwn(config.rules, ruleId)) {
  ruleOptions = [ruleOptions[0], ...config.rules[ruleId].slice(1)];
  if (config.rules[ruleId][0] > 0) shouldValidateOptions = false;  // already validated once
} else {
  const mergedOptions = deepMergeArrays(rule.meta?.defaultOptions, ruleOptions.slice(1));
  if (mergedOptions.length) ruleOptions = [ruleOptions[0], ...mergedOptions];
}
```

**Flow:** `applyInlineConfig()` problems become FATAL messages; a second config comment for the same rule is an error and ignored; unknown inline rules are reported errors, not throws; validation errors are downgraded to per-location report errors EXCEPT `ESLINT_INVALID_RULE_OPTIONS_SCHEMA` (rethrown — bad schema is a rule bug) and `rule-unsupported-language` (actionable message). After merging, `sourceCode.finalize?.()`, then `runRules`, then `applyDisableDirectives` with line/column-sorted messages.
**Invariant:** severity-only splices must NOT deep-merge defaults again (config options already beat defaults); skipping revalidation for previously-enabled rules is what keeps repeated inline comments cheap AND idempotent; inline configs accumulate in document order and first-writer-wins per rule.
**Probe:** `tests/lib/linter/linter.js` (:3940–4110 severity-retention incl. :4034/:4074 + :4110–4399 `/* eslint */` suites — options retention under severity-only override :4110, unused-inline-config reporting :4137/:4261/:4305).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "mergedInlineConfig applyInlineConfig warnInlineConfig validateRulesConfig", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.linter.addProblemIfSameSeverityAndOptions" });
```

## Verdict
Adopt the severity-splice-with-options-retention ladder and the fatal-vs-error triage of inline problems; adapt comment grammar to your host; omit unused-inline-config linting unless you want the strictness.
