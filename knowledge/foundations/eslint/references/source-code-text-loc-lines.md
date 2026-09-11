<!-- capsule-v2 -->
# SourceCode text/line index — how do you convert between character offsets and {line,column} across every ECMA-262 line terminator?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** How does SourceCode build its line table and keep offset↔location conversions exact and symmetric, including end-of-file?

## Line splitting + binary-search conversions
**Path/Symbol:** `lib/languages/js/source-code/source-code.js` constructor split (:388–417), `findLineNumberBinarySearch` (:176–191), `getLocFromIndex` (:541–579), `getIndexFromLoc` (:592–649), `getText` (:438–446).
**Signature:** `getLocFromIndex(index): {line, column}` (1-based line, 0-based column); `getIndexFromLoc({line, column}): number`; `getText(node?, beforeCount?, afterCount?): string`.
**Data Shape:** `lineStartIndices = [0]`, one push per terminator at `match.index + match[0].length` (so an entry points AFTER the terminator; CRLF is one entry); `lines` holds the text BETWEEN terminators and is frozen with `Object.freeze(this)`.

### Decisive source
```js
// Constructor — match ONLY newlines; comment preserved from source:
// "this caused a catastrophic backtracking issue when the end of a file contained
//  a large number of non-newline characters. To avoid this, the current
//  implementation just matches newlines and uses match.index."
while ((match = lineEndingPattern.exec(this.text))) {   // /
|[


]/gu
  this.lines.push(this.text.slice(this.lineStartIndices.at(-1), match.index));
  this.lineStartIndices.push(match.index + match[0].length);
}
// getLocFromIndex — past-end special case pairs with getIndexFromLoc:
if (index === this.text.length) {
  return { line: this.lines.length, column: this.lines.at(-1).length };
}
// getIndexFromLoc — column may EQUAL line length only on the LAST line:
if ((loc.line === this.lineStartIndices.length && positionIndex > lineEndIndex) ||
    (loc.line <  this.lineStartIndices.length && positionIndex >= lineEndIndex)) {
  throw new RangeError(`Column number out of range ...`);
}
return positionIndex;
```

**Flow:** constructor validates AST (tokens/comments/loc/range present), retypes a leading shebang comment to type "Shebang", sorted-merges tokens+comments once, then builds lines + lineStartIndices → getLocFromIndex finds the line by upper-bound binary search over starts (`index >= last start ⇒ last line`) → getIndexFromLoc validates 1-based line/column and adds.
**Invariant:** the two conversions are exact inverses for EVERY index in [0, text.length] (test loops all of them); "one spot past end" round-trips as {lastLine+? , col} ⇄ text.length. getText clamps only the LEFT edge (`Math.max(range[0]-(beforeCount||0), 0)`); the right edge relies on slice tolerance. A porter who splits on \n alone breaks CRLF/LS/PS files; one who consumes line CONTENT in the regex reintroduces the documented backtracking blowup.
**Probe:** `tests/lib/languages/js/source-code/source-code.js` (:952–1028 mixed \\n \\r\\n \\r \\u2028 \\u2029 matrix, symmetry loop :1019–1028, past-end :1005–1010; :404–408 left-clamp). Executed at pin: subset --grep 'getLocFromIndex|getIndexFromLoc|getText' → 18 passing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "SourceCode getLocFromIndex getIndexFromLoc lineStartIndices findLineNumberBinarySearch", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.languages.js.source-code.source-code.SourceCode.getLocFromIndex" });
```

## Verdict
Adopt the newline-only matcher + upper-bound search + paired past-end special cases wholesale for any editor-grade offset↔position table. Adapt the frozen-lines representation to host. Omit shebang retyping if the host parser already classifies it (ESLint needs it because espree sees "//…" comments only).
