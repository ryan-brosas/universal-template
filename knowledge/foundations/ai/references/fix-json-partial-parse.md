<!-- capsule-v2 -->
# fixJson + parsePartialJson — how do you parse a HALF-STREAMED JSON object into a usable value, and repair truncated JSON in ONE linear pass without a real parser?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** When a model's JSON answer arrives token-by-token (or truncated), how do you produce every intermediate valid value and classify each parse as exact vs repaired — the substrate every partial-object stream sits on?

## Linear scanner-repairer (`fixJson`)
**Path/Symbol:** `packages/ai/src/util/fix-json.ts:fixJson` (:28–430).
**Signature:** `function fixJson(input: string): string` — pure, single forward scan.
**Data Shape:** Input = any string (usually accumulated model text). Output = a BEST-EFFORT complete JSON string: input sliced at `lastValidIndex` (last char that left the parser in a still-valid state) plus synthesized closers for whatever the state stack still holds. Invalid-but-complete JSON is deliberately NOT corrected — "it is assumed that the resulting JSON will be processed by a standard JSON parser that will detect any invalid JSON" (header comment :19–27).

### Decisive source
```ts
// stack of JSON-spec states drives everything; lastValidIndex marks the
// longest prefix that is still valid JSON so far:
const stack: State[] = ['ROOT'];
let lastValidIndex = -1;
// ...single pass; INSIDE_STRING '"' pops back to the value state; escapes push
// INSIDE_STRING_ESCAPE / 4-hex-digit INSIDE_STRING_UNICODE_ESCAPE
// ...after the loop: truncate to last valid char, then CLOSE what's open,
// from innermost outward (reverse stack walk):
let result = input.slice(0, lastValidIndex + 1);
for (let i = stack.length - 1; i >= 0; i--) {
  switch (stack[i]) {
    case 'INSIDE_STRING': result += '"'; break;
    case 'INSIDE_OBJECT_KEY':          // ...all open-object states...
    case 'INSIDE_OBJECT_AFTER_VALUE':  result += '}'; break;
    case 'INSIDE_ARRAY_AFTER_VALUE':   result += ']'; break;
    case 'INSIDE_LITERAL': {           // complete a torn literal by prefix:
      const partialLiteral = input.substring(literalStart!, input.length);
      if ('true'.startsWith(partialLiteral)) result += 'true'.slice(partialLiteral.length);
      else if ('false'.startsWith(partialLiteral)) /* ... */
      else if ('null'.startsWith(partialLiteral))  /* ... */
    }
  }
}
```
Torn-literal handling works mid-scan too: `INSIDE_LITERAL` pops as soon as the accumulated text stops being a prefix of `true`/`false`/`null` (:363–383), and `INSIDE_NUMBER` tolerates `e/E/-/.` continuations while treating `,`/`}`/`]` as number terminators that re-dispatch to the enclosing container state (:297–361).

**Flow:** classification lives in `parse-partial-json.ts:parsePartialJson` (:5–30, whole file): try plain `safeParseJSON(text)` → on failure `safeParseJSON(fixJson(text))` → return `{value, state}` with state ∈ `undefined-input | successful-parse | repaired-parse | failed-parse` (`failed-parse` ⇒ value undefined). An EXACT parse of already-complete JSON never pays for the scanner.
**Invariant:** The repaired string is built ONLY from characters proven to keep the document parseable (`lastValidIndex`) plus mechanical closers — never by deleting interior content. A porter who "fixes" by dropping the trailing incomplete token instead of slicing at lastValidIndex will emit values a real parser rejects. Callers downstream branch on the STATE STRING (see stream-object-pipeline.md: isFinalDelta = state==='successful-parse'), so collapsing the two success states breaks partial-stream semantics.
**Probe:** `packages/ai/src/util/parse-partial-json.test.ts` — nullish input :11; valid JSON stays `successful-parse` :18; `'{"key": "value"'` → `repaired-parse` with `fixJson` called between the two safeParseJSON calls :35; unrepairable garbage → `{value: undefined, state: 'failed-parse'}` :62 (suite mocks safeParseJSON/fixJson to pin ORCHESTRATION; fixJson character behavior itself is pinned transitively by stream-object/output suites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "fixJson parsePartialJson repair partial json", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the four-state classification and the slice-at-lastValidIndex + reverse-stack-closer repair shape verbatim (pure, linear, dependency-free); adapt the state list if your host grammar differs; omit the unicode-escape sub-state only if your consumers never split `\uXXXX` across chunks. Coverage caveat: index best-effort; excerpts read directly at HEAD.
