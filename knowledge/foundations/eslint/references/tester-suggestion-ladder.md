<!-- capsule-v2 -->
# RuleTester suggestion assertion ladder — the complete per-suggestion contract from desc/messageId exclusivity to output-differs

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** For each expected suggestion on an invalid case, which assertions run and in what order?

## Suggestion matrix (testInvalidTemplate)
**Path/Symbol:** `lib/rule-tester/rule-tester.js:testInvalidTemplate` suggestion block (:1415+) — uniqueness Map (:1442–1470), shape gates (:1632–1660), desc-vs-messageId branches (:1687–1731), data-rehydration (:1761–1781), requireData gate (:1795–1813), output application + re-lint (:1816+).
**Signature:** `errors[i].suggestions: number | Array<{desc?|messageId?, data?, output}>`.
**Data Shape:** `desc` XOR `messageId` (both or neither fail); `data` requires `messageId` form; `output` REQUIRED on every entry; `suggestions: 0/false` asserts absence, number asserts count.

### Decisive source
```js
const seenMessageIndices = new Map();          // desc-string uniqueness within ONE message
assert.ok(!seenMessageIndices.has(suggestionMessage),
  `Suggestion message '${suggestionMessage}' reported from suggestion ${i} was previously
   reported by suggestion ${previous}. Suggestion messages should be unique within an error.`);
// messageId branch: must exist in rule.meta.messages; rehydrate template with test data via
// interpolate(rawSuggestionMessage, expectedSuggestion.data) and deep-compare to actual desc;
// unsubstituted placeholders after interpolation ⇒ failure naming the missing key(s)
// then: applyFixes(item.code, [actualSuggestion]) → linter.verify → no fatal allowed;
//       strictEqual(applied, expectedSuggestion.output);
//       notStrictEqual(expectedSuggestion.output, item.code)  // "no-op suggestion" is a failure
```

**Flow:** presence gate (`message.suggestions` requires `error.suggestions`) → count/absence → per-entry: property allowlist {desc,messageId,data,output} → desc-or-messageId → uniqueness by resolved desc string → placeholder/data reconciliation → individual fix application → fatal re-lint → byte-equal output → differs-from-source.
**Invariant:** suggestions are validated as INDEPENDENT fixes against the ORIGINAL code (not cumulative), so order-independence of each suggestion is enforced. Uniqueness keys on the DESC STRING after interpolation — two suggestions may share messageId if their data renders differently. The differs-from-source assert catches rules emitting "suggestions" that change nothing (test-smell policing). errorIndex/scenarioIndex tagging lands on every thrown assertion for tester location attribution.
**Probe:** `tests/lib/rule-tester/rule-tester.js` (:4119 uniqueness failure text; :3895 "Test should not specify both 'desc' and 'data'" pairs; :3824 hydrated-desc mismatch; :7356 location attribution when a SUGGESTION assertion fails).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "suggestions seenMessageIndices rehydratedDesc applyFixes suggestion", limit: 10 });
```

## Verdict
Adopt the full ladder for any engine with code-action suggestions; the uniqueness-by-rendered-desc and differs-from-source checks are the two most-copied invariants.
