<!-- capsule-v2 -->
# Autofix loop — how do you apply rule fixes safely, converge, and detect circular fix cycles?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you merge overlapping fixes from independent rules into one new text without corruption or infinite loops?

## SourceCodeFixer.applyFixes
**Path/Symbol:** `lib/linter/source-code-fixer.js:SourceCodeFixer.applyFixes` (:61–152).
**Signature:** `applyFixes(sourceText, messages, shouldFix): { fixed, messages, output }`.
**Data Shape:** fixes are `{ range:[start,end], text }` with half-open character offsets; BOM is split off before applying and re-prepended; `shouldFix` is boolean or a per-message predicate.

### Decisive source
```js
for (const problem of fixes.sort(compareMessagesByFixRange)) {
  if (typeof shouldFix !== "function" || shouldFix(problem)) {
    attemptFix(problem);
    // The only time attemptFix will fail is if a previous fix was
    // applied which conflicts with it. So we can mark this as true.
    fixesWereApplied = true;
  } else {
    remainingMessages.push(problem);
  }
}
// inside attemptFix:
if (lastPos >= start || start > end) { remainingMessages.push(problem); return false; }
```

**Flow:** partition messages into fixable/unfixable → sort fixes by range start → sweep once, emitting text up to each accepted fix and advancing `lastPos` past its range → overlaps/negative ranges fall back to `remainingMessages` → return unfixed messages re-sorted by line/column.
**Invariant:** one pass applies only non-overlapping fixes — an overlapped fix is deferred, never merged; the next verify+apply iteration may land it. `fixed:true` even when the single attempted fix conflicted, so callers keep looping.
**Probe:** `tests/lib/linter/source-code-fixer.js` (overlap deferral, BOM handling, sort order).

## verifyAndFix convergence
**Path/Symbol:** `lib/linter/linter.js:Linter.verifyAndFix` (:1488–1625).
**Signature:** `verifyAndFix(text, config, filenameOrOptions?): { fixed, messages, output }`.
**Data Shape:** `MAX_AUTOFIX_PASSES = 10`; keeps `previousText` and `secondPreviousText`; stats mode tracks per-pass times + `fixPasses`.

### Decisive source
```js
do {
  passNumber++;
  messages = this.verify(currentText, config, options);
  fixedResult = SourceCodeFixer.applyFixes(currentText, messages, shouldFix);
  if (messages.length === 1 && messages[0].fatal) break;      // syntax error: bail, don't loop on garbage
  secondPreviousText = previousText;
  previousText = currentText;
  currentText = fixedResult.output;
  if (passNumber > 1 && currentText.length === secondPreviousText.length &&
      currentText === secondPreviousText) {
    // Circular fixes detected after pass ${passNumber}. Exiting fix loop.
    slots.warningService.emitCircularFixesWarning(options.filename ?? "text");
    break;
  }
} while (fixedResult.fixed && passNumber < MAX_AUTOFIX_PASSES);
```

**Flow:** verify → apply fixes → stop on fatal parse error / no-progress / A→B→A cycle / 10-pass cap → one final verify after the last fixing pass so reported messages match the emitted output.
**Invariant:** cycle detection compares against the *second-previous* text (A→B→A oscillation would evade last-text comparison); the fatal-message break prevents re-linting unparseable output forever; final re-verify guarantees `messages` describe `output`, not the input.
**Probe:** `tests/lib/linter/linter.js` (`verifyAndFix` — max passes, circular-fix warning, fatal break).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "verifyAndFix SourceCodeFixer applyFixes", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.linter.Linter.verifyAndFix" });
```

## Verdict
Adopt the sorted non-overlap sweep + two-back cycle detection + fatal-parse break + post-loop re-verify; adapt the warning service and pass cap to host policy; omit ESLint's `meta.fixable`/whitespace-fix metadata enforcement unless porting rule authoring too.
