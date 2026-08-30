<!-- capsule-v2 -->
# Verify option normalization + error attribution — how do verify options become one normalized shape, and how do traversal failures name the file, line, and rule?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you fold boolean/string config tri-state into one internal options object and make mid-traversal exceptions debuggable?

## normalizeVerifyOptions + error decoration
**Path/Symbol:** `lib/linter/linter.js:normalizeVerifyOptions` (:352–408), `normalizeFilename` (:338–343), `runRules` catch-decoration in `#flatVerifyWithoutProcessors` (:1280–1298), traverser-side `err.currentNode` stamping (`source-code-traverser.js:312–315`), rule-side `err.ruleId` (`linter.js:642–665 addRuleErrorHandler`), `_distinguishSuppressedMessages` (:1429–1445).
**Signature:** `normalizeVerifyOptions(providedOptions, config) → {filename, allowInlineConfig, warnInlineConfig, reportUnusedDisableDirectives, reportUnusedInlineConfigs, disableFixes, stats, ruleFilter}`.
**Data Shape:** `reportUnusedDisableDirectives` collapses three layers (option bool→string, linterOptions.bool→"warn"/"off", else severity string); `ruleFilter` defaults to `() => true`; filename defaults `<input>` with `/path/to/<text>` suffix-normalization.

### Decisive source
```js
// three-layer normalization ladder:
if (typeof reportUnusedDisableDirectives === "boolean")
  reportUnusedDisableDirectives = reportUnusedDisableDirectives ? "error" : "off";
if (typeof reportUnusedDisableDirectives !== "string") {
  if (typeof linterOptions.reportUnusedDisableDirectives === "boolean")
    reportUnusedDisableDirectives = linterOptions.reportUnusedDisableDirectives ? "warn" : "off";
  else
    reportUnusedDisableDirectives = linterOptions.reportUnusedDisableDirectives === void 0
      ? "off" : normalizeSeverityToString(linterOptions.reportUnusedDisableDirectives);
}
// failure decoration accumulates across three layers:
catch (err) {
  err.message += `\nOccurred while linting ${options.filename}`;
  if (err.currentNode) err.message += `:${sourceCode.getLoc(err.currentNode).start.line}`;
  if (err.ruleId)     err.message += `\nRule: "${err.ruleId}"`;
  throw err;
}
```

**Flow:** verify() normalizes once up front; the traverser stamps the failing node, the rule wrapper stamps the rule id, and the linter catch appends file+line before rethrowing — so a porter gets rule→node→file attribution without stack-trace archaeology. After directive filtering, `_distinguishSuppressedMessages` partitions problems into returned messages vs slot-stored suppressed ones (consumable via `getSuppressedMessages()`).
**Invariant:** options normalization must be total — downstream code pattern-matches exact strings ("off"/"warn"/"error"), never booleans; error decoration is ADDITIVE through layers (each layer may enrich but never swallows); suppressed messages are stored on instance slots, not dropped, because RuleTester and formatters read them back.
**Probe:** `tests/lib/linter/linter.js` (:2516 Rule Severity + :2629 Options suites; :9634 getSuppressedMessages suite); `tests/lib/linter/source-code-traverser.js` (:352–371 currentNode stamping observable via thrown err).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "normalizeVerifyOptions _distinguishSuppressedMessages addRuleErrorHandler", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.linter.normalizeVerifyOptions" });
```

## Verdict
Adopt the single-normalized-options boundary and three-layer error attribution; adapt severity vocabulary; omit the suppressed-messages slot if your host has no suppression UI.
