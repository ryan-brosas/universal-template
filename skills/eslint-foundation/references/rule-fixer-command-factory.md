<!-- capsule-v2 -->
# Fix command factory — how do you build fix objects so a porter never emits malformed ranges?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** What is the exact contract of the fixer object handed to rules, and which validations happen at creation vs application time?

## RuleFixer command constructors
**Path/Symbol:** `lib/linter/rule-fixer.js:RuleFixer` (:60–197) + module helper `insertTextAt(index, text)` (:34–44) + `assertIsString(text)` (:47–56).
**Signature:** `insertTextBefore/After(nodeOrToken, text)`, `insertTextBefore/AfterRange(range, text)`, `replaceText(nodeOrToken, text)`, `replaceTextRange(range, text)`, `remove(nodeOrToken)`, `removeRange(range)` — all return plain `{ range:[start,end], text }`.
**Data Shape:** ranges are half-open 0-based character offsets into the ORIGINAL source; insertions are zero-width ranges `[i,i]`; removals are `text:""`. The fixer holds ONLY a `sourceCode` (private `#sourceCode`) — node→range resolution goes through `sourceCode.getRange(nodeOrToken)`.

### Decisive source
```js
function insertTextAt(index, text) { return { range: [index, index], text }; }
// every text-taking method calls assertIsString(text) FIRST:
if (typeof text !== "string") throw new TypeError("'text' must be a string");
insertTextAfterRange: (range, text) => insertTextAt(range[1], text);   // AFTER = at end offset
insertTextBeforeRange: (range, text) => insertTextAt(range[0], text);  // BEFORE = at start offset
```

**Flow:** node/token variants resolve the range via sourceCode then delegate to the *Range variants → Range variants are one-liners that shape the command; nothing here mutates source or checks overlap.
**Invariant:** validation is TYPE-only and eager (`text` must be a string), but RANGE sanity (start ≤ end, non-overlap, in-bounds) is NOT checked here — it is enforced later by SourceCodeFixer.applyFixes' sweep. A porter who adds range validation here changes nothing observable but a porter who DROPS assertIsString lets `undefined` fixes silently produce "undefined" text. After-vs-before differs only in which offset the zero-width range sits on — swapping them corrupts insertion order relative to other fixes.
**Probe:** `tests/lib/linter/rule-fixer.js` (:35–57 insertTextBefore incl. empty-text + non-string-throw; :61–105 after-variants; :113–196 replace/remove matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "RuleFixer insertTextAfterRange replaceTextRange removeRange", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.rule-fixer.RuleFixer.replaceTextRange" });
```

## Verdict
Adopt the plain-command data shape ({range,text}), the type-check-at-construction / overlap-check-at-application split, and the before=end/after=start offset convention; adapt method names to host style; omit the class entirely if your engine passes raw commands to rules.
