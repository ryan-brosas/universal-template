<!-- capsule-v2 -->
# Unused-directive reporting — how do you prove an `eslint-disable` was unnecessary and generate a whitespace-preserving removal fix?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you decide a disable/enable comment was unused, and how do you build removal fixes that keep the rest of the comment intact?

## applyDirectives + processUnusedDirectives
**Path/Symbol:** `lib/linter/apply-disable-directives.js:applyDirectives` (:311–437), `processUnusedDirectives/createDirectiveRemoval/createIndividualDirectivesRemoval` (:189–214, :164–181, :65–155), `collectUsedEnableDirectives` (:221–299), `groupByParentDirective` (:40–56), entry `module.exports` (:463–583).
**Signature:** `applyDisableDirectives({language, sourceCode, directives, disableFixes, problems, configuredRules, ruleFilter, reportUnusedDisableDirectives}) → problems[]` (unused-directive problems appended when severity ≠ "off").
**Data Shape:** two independent passes — block directives (`disable|enable`, sorted by location) then line directives (each `disable-line`/`disable-next-line` desugared to an enable/disable pair with `unprocessedDirective` backlink). A problem suppressed by ≥1 directive carries `suppressions: [{kind:"directive", justification}]`; only the FIRST suppressing directive counts as "used".

### Decisive source
```js
// mid-list element removal keeps surrounding commas/format:
const regex = new RegExp(
  String.raw`(?:^|\s*,\s*)(?<quote>['"]?)${escapeRegExp(ruleId)}\k<quote>(?:\s*,\s*|$)`, "u");
// two commas ⇒ strip between them incl. ONE comma; single/edge ⇒ strip matched span
removalStart = matchStart + firstIndexOfComma;   // middle elements
removalEnd   = matchStart + lastIndexOfComma;
// whole-comment removal replaces the node range with a SINGLE SPACE:
fix: { range: sourceCode.getRange(node), text: " " }
```

**Flow:** per problem, scan directives ≤ its location collecting active disables (an `enable` RESETS the collected set); suppress + mark last-disable used. Unused disables and enables become problems only when `reportUnusedDisableDirectives !== "off"`; `ruleFilter`-excluded rules are added to `rulesToIgnore` (plus `null` for all-rules directives) so filtering never manufactures false "unused" reports. Enable usage is decided by a REVERSE walk pairing enables with later disables.
**Invariant:** fixes preserve author formatting byte-for-byte outside removed spans (quote-matched regex, comma-boundary logic); `disableFixes:true` omits the fix field entirely rather than emitting a no-op; unused-directive problems carry `ruleId:null`.
**Probe:** `tests/lib/linter/apply-disable-directives.js` (:1156–2968 unused-directive matrix — 38 its with exact message/fix/severity assertions; :2969+ rules-filtered non-reporting).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "applyDirectives collectUsedEnableDirectives createIndividualDirectivesRemoval rulesToIgnore", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.apply-disable-directives.processUnusedDirectives" });
```

## Verdict
Adopt used-on-first-suppression semantics, reverse-walk enable liveness, and format-preserving removal ranges; adapt directive grammar; omit rulesToIgnore plumbing if you have no rule filter.
