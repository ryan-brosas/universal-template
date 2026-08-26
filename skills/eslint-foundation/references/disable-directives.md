<!-- capsule-v2 -->
# Disable directives — how do `eslint-disable` / `enable` / `-line` / `-next-line` comments suppress problems, and how are unused ones reported?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you suppress reported problems by comment location without losing the audit trail?

## Directive application
**Path/Symbol:** `lib/linter/apply-disable-directives.js:module.exports` (:463–583) + `applyDirectives` (:311–437).
**Signature:** `applyDisableDirectives({ language, sourceCode, directives, disableFixes, problems, configuredRules, ruleFilter, reportUnusedDisableDirectives="off" }): problems[]`.
**Data Shape:** directives `{type: "disable"|"enable"|"disable-line"|"disable-next-line", ruleId: string|null, line, column}`; `disable-line` desugars to disable@line+enable@line+1; `disable-next-line` to disable@line+1+enable@line+2 (both with `column: 0` enables); problems must arrive sorted by location.

### Decisive source
```js
while (nextDirectiveIndex < options.directives.length &&
       compareLocations(options.directives[nextDirectiveIndex], problem) <= 0) {
  const directive = options.directives[nextDirectiveIndex++];
  if (directive.ruleId === null || directive.ruleId === problem.ruleId) {
    switch (directive.type) {
      case "disable": disableDirectivesForProblem.push(directive); break;
      case "enable":  disableDirectivesForProblem = [];            break;
    }
  }
}
if (disableDirectivesForProblem.length > 0) {
  problem.suppressions = suppressions;   // kept on the message, split out later
  usedDisableDirectives.add(disableDirectivesForProblem.at(-1));
}
```

**Flow:** split block vs line directives (line kinds desugar into enable/disable pairs carrying the original as `unprocessedDirective`) → sort both by location → single forward sweep per problem collecting open disables until an enable clears them → matched problems get a `suppressions` array instead of deletion → unused disable/enable directives become fixable reports (whole-comment removal when every listed rule is unused, else comma-span excision that preserves surrounding whitespace).
**Invariant:** suppression *marks* messages (`problem.suppressions`) rather than removing them — `_distinguishSuppressedMessages` later splits them into `getSuppressedMessages()`, so nothing is silently dropped. A bare `eslint-disable` consumes all pending scoped enables. Unused-directive reporting is skipped for rules excluded by `ruleFilter` (`rulesToIgnore`, including `null` for rule-less directives) so filtering never manufactures "unused" noise.
**Probe:** `tests/lib/linter/apply-disable-directives.js` (desugaring, sweep, unused-directive fix ranges).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "applyDisableDirectives suppressions unused directive", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.apply-disable-directives.applyDirectives" });
```

## Verdict
Adopt the mark-then-split suppression model, line-kind desugaring, and whitespace-preserving removal fixes; adapt severity of unused-directive reports and justification storage to host; omit the `ruleFilter` interplay if your host has no rule filtering.
