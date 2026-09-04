<!-- capsule-v2 -->
# Stream filtering — teaching the model manners at read time with a composable transform pipeline

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does Continue clean LLM output AS IT STREAMS (before postprocessing), composing char-level and line-level filters so conversational wrappers, bracket breaks, and repetitions are stopped at semantic boundaries?

## The StreamTransformPipeline
**Path/Symbol:** `core/autocomplete/filtering/streamTransforms/StreamTransformPipeline.ts:transform` (21–83).
**Signature:** `transform(generator, prefix, suffix, multiline, stopTokens, fullStop, helper): AsyncGenerator<string>`.
**Data Shape:** wraps an `AsyncGenerator<string>` in successive filter layers; each layer is an async generator transform; `fullStop` is a callback to terminate the whole stream.

### Decisive source
```ts
let charGenerator = generator;
charGenerator = stopAtStopTokens(charGenerator, [...stopTokens, ...STOP_AT_PATTERNS]); // "diff --git"
charGenerator = stopAtStartOf(charGenerator, suffix);          // stop when output reaches the suffix
for (const charFilter of helper.lang.charFilters ?? []) charGenerator = charFilter({chars: charGenerator, prefix, suffix, filepath, multiline});
let lineGenerator = streamLines(charGenerator);
lineGenerator = stopAtLines(lineGenerator, fullStop);
if (lineBelowCursor.trim() !== "") lineGenerator = stopAtLinesExact(lineGenerator, fullStop, [lineBelowCursor]);
lineGenerator = stopAtRepeatingLines(lineGenerator, fullStop);
lineGenerator = avoidEmptyComments(lineGenerator, helper.lang.singleLineComment);
lineGenerator = avoidPathLine(lineGenerator, helper.lang.singleLineComment);
lineGenerator = skipPrefixes(lineGenerator);          // PREFIXES_TO_SKIP = ["<COMPLETION>"]
lineGenerator = noDoubleNewLine(lineGenerator);
for (const lineFilter of helper.lang.lineFilters ?? []) lineGenerator = lineFilter({lines: lineGenerator, fullStop});
lineGenerator = stopAtSimilarLine(lineGenerator, this.getLineBelowCursor(helper), fullStop);
lineGenerator = showWhateverWeHaveAtXMs(lineGenerator, helper.options.modelTimeout!);
const finalGenerator = streamWithNewLines(lineGenerator);
```

**Flow:** char-level filters run first (stop tokens, stop-at-suffix, per-language char filters), then line-level filters (stop at known lines, exact line below cursor, repeating lines, empty comments, path lines, skip prefixes, no double newline, per-language line filters, similar line, timeout flush). `getLineBelowCursor` scans downward past blank lines for the first non-blank line under the cursor and stops when the model reproduces it.

**Invariant:** filters compose in a fixed order — char-level before line-level, generic before language-specific; `fullStop` is the single abort mechanism shared by all stopping filters; `validatePatternInLine` (lineStream.ts:62) only treats a stop pattern as valid if it is NOT preceded by a non-whitespace char (identifier guard) and NOT inside quotes (odd-quote-count heuristic).

**Probe:** `core/autocomplete/filtering/streamTransforms/lineStream.vitest.ts` (1,301 lines) — `avoidPathLine` filters path lines, `avoidEmptyComments` filters empty comments, `streamWithNewLines` adds newlines, `lineIsRepeated` detects similar lines; `filterCodeBlock.vitest.ts` (452 lines); `testCases.ts` (~2,200 lines) harvests real failure heuristics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "StreamTransformPipeline transform lineStream", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the composable char→line filter pipeline, the stop-at-suffix and stop-at-line-below-cursor invariants, the `fullStop` abort mechanism, and the identifier/quote validation heuristic; adapt the language-specific char/line filter sets and stop-pattern lists to host; omit nothing portable — the pipeline is language-agnostic with per-language hooks. Coverage caveat: graph metadata `metadata_match`; heavy vitest coverage.
