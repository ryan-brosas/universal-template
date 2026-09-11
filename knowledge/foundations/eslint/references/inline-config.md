<!-- capsule-v2 -->
# Inline-config merge — how does a `/* eslint */` comment override severity while retaining configured options?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do inline rule comments merge with file config without double-validating or clobbering options?

## Severity-only override ladder
**Path/Symbol:** `lib/linter/linter.js:#flatVerifyWithoutProcessors` inline-config block (:1046–1259, decisive range :1129–1192).
**Signature:** merged into `configuredRules = Object.assign({}, config.rules, mergedInlineConfig.rules)` (:1255–1259).
**Data Shape:** inline value is `[severity, ...options?]`; `mergedInlineConfig` starts as `{ rules: {} }`; duplicate inline configs for the same rule ⇒ error + the later one ignored.

### Decisive source
```js
if (
  ruleOptions.length === 1 &&          // inline config has ONLY severity
  config.rules && Object.hasOwn(config.rules, ruleId)   // and rule was already configured
) {
  ruleOptions = [
    ruleOptions[0],                    // severity from the inline config
    ...config.rules[ruleId].slice(1),  // options from the provided config
  ];
  // if the rule was enabled, the options have already been validated
  if (config.rules[ruleId][0] > 0) shouldValidateOptions = false;
}
```

**Flow:** `sourceCode.applyInlineConfig()` yields `{configs, problems}` → problems become fatal reports → per inline rule: unknown rule ⇒ error; already-configured-by-another-comment ⇒ error+skip; severity-only ⇒ splice file-config options under the new severity (validation skipped when previously enabled); options present ⇒ `deepMergeArrays(rule.meta.defaultOptions, slicedOptions)` then full schema validation.
**Invariant:** an inline `/* eslint curly: ["warn"] */` over `curly: ["error", "multi"]` yields `["warn", "multi"]` — options survive the severity change. Validation is skipped *only* because the enabled file-config options were already validated in `Config` construction; re-validating merged arrays that contain non-JSON values would throw spuriously.
**Probe:** `tests/lib/linter/linter.js` (inline severity-override retention cases around this exact example).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "applyInlineConfig mergedInlineConfig validateRulesConfig", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.linter.Linter._verifyWithFlatConfigArrayAndWithoutProcessors" });
```

## Verdict
Adopt the severity-splice-with-option-retention merge and its skip-revalidation gate; adapt the fatal-vs-error reporting of malformed comments to host; omit `reportUnusedInlineConfigs` bookkeeping unless porting lint hygiene reporting.
