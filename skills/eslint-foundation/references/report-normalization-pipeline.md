<!-- capsule-v2 -->
# Report normalization pipeline — how does one `context.report()` call become a finished LintMessage with fix, suggestions, and 1-based locations?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** What is the exact normalization ladder from a rule's report descriptor to the message object consumers see?

## FileReport.addRuleMessage
**Path/Symbol:** `lib/linter/file-report.js:FileReport` (:475–599) — `addRuleMessage` (:530–564), `addError/addWarning/addFatal` (:571–598); helpers `normalizeMultiArgReportCall` (:135–160), `computeMessageFromDescriptor` (:440–469), `validateSuggestions` (:395–431), `normalizeFixes/mergeFixes/cloneFix` (:197–305), `mapSuggestions` (:314–335), `createProblem` (:350–387), `updateLocationInformation` (:67–85).
**Signature:** `addRuleMessage(ruleId, severity, ...args): LintMessage`; args accept new-style single descriptor or legacy positional `[node, message|loc, data?, fix?]`.
**Data Shape:** fixes `{range:[s,e], text}` half-open offsets; suggestions carry `desc|messageId` + fix fn; language objects declare `columnStart/lineStart` (0 vs 1) so every emitted line/column is rebased to 1-based.

### Decisive source
```js
const computedMessage = computeMessageFromDescriptor(descriptor, messages); // messageId xor message
validateSuggestions(descriptor.suggest, messages);
this.messages.push(createProblem({
  ruleId, severity,
  message: interpolate(computedMessage, descriptor.data),
  loc: descriptor.loc ? normalizeReportLoc(descriptor) : this.#sourceCode.getLoc(descriptor.node),
  fix:   this.#disableFixes ? null : normalizeFixes(descriptor, this.#sourceCode),
  suggestions: this.#disableFixes ? [] : mapSuggestions(descriptor, this.#sourceCode, messages),
  language: this.#language,
}));
// mergeFixes: sort by range, splice original text BETWEEN fixes, assert non-overlap:
assert(fix.range[0] >= lastPos, "Fix objects must not be overlapped in a report.");
```

**Flow:** normalize legacy arity → assert node-or-loc → resolve message (messageId must exist in `meta.messages`; both given ⇒ TypeError) → validate each suggestion (needs desc-or-messageId, never both, fix must be a function) → run fix through a per-call RuleFixer; iterable results merge into ONE fix spanning first-start→last-end with source text re-spliced between → interpolate data placeholders → map suggestions (drop ones whose fix resolved falsy) → create problem with optional fields (`messageId`, `endLine/endColumn`, `fix`, `suggestions`) present only when set. Non-rule entries: `addError` (missing-rule text via conf/replacements.json), `addFatal` (adds `fatal:true`), `addWarning`.
**Invariant:** fix merging asserts NON-overlap at report time — overlapping fixes from one report are an authoring bug, not a runtime conflict (runtime overlap is the autofix loop's job); `disableFixes` nulls the fix AND empties suggestions but keeps the message; locations are stored 0-based internally and offset once, here.
**Probe:** `tests/lib/linter/file-report.js` (:647–853 array+iterator merging with byte-exact merged text "fooo\nbar" :669/:695; :1416+ validation TypeErrors; :1773 updateLocationInformation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "FileReport addRuleMessage mergeFixes mapSuggestions computeMessageFromDescriptor", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.file-report.FileReport.addRuleMessage" });
```

## Verdict
Adopt the two-phase validate-then-normalize pipeline and single-fix-per-report merging; adapt severity vocab and interpolation to your host; omit legacy positional-descriptor support if you control all rules.
