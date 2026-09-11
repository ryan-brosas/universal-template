<!-- capsule-v2 -->
# Char-stream stop primitives — stop-token buffer drain, suffix-prefix detection with 1.5× tolerance, EOL+non-whitespace cut

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** What are the exact character-level rules for cutting an LLM stream at stop tokens, at the start of existing suffix text, and at end-of-line followed by real content?

## Key facts
**Path/Symbol:** `core/autocomplete/filtering/streamTransforms/charStream.ts` (whole, 163L) — `onlyWhitespaceAfterEndOfLine` (:11-41), `noFirstCharNewline` (:48-59), `stopAtStopTokens` (:76-119), `stopAtStartOf` (:125-163); direct suite `charStream.vitest.ts` (stopAtStopTokens describe :18, 12 cases; stopAtStartOf :152).
**Signature:** all four are `async function*` generators over `AsyncGenerator<string>`; `stopAtStopTokens(stream, stopTokens)`, `stopAtStartOf(stream, suffix, sequenceLength=20)`, `onlyWhitespaceAfterEndOfLine(stream, endOfLine: string[], fullStop: () => void)`.
**Data Shape:** char/chunk-level buffers; `endOfLine` is per-language token list (e.g. Json `[",", "}", "]"]`, Markdown `[]`).

### Decisive source
```ts
// :87-108 — hold back maxStopTokenLength chars; emit only confirmed-safe prefix:
const maxStopTokenLength = Math.max(...stopTokens.map((t) => t.length));
let buffer = "";
for await (const chunk of stream) {
  buffer += chunk;
  while (buffer.length >= maxStopTokenLength) {
    for (const stopToken of stopTokens)
      if (buffer.startsWith(stopToken)) return;      // stop BEFORE emitting it
    yield buffer[0]; buffer = buffer.slice(1);       // emit one confirmed char
  }
}
// :111-113 — tail flush strips any stop token that arrived whole:
stopTokens.forEach((token) => { buffer = buffer.replace(token, ""); });

// :136-140 — suffix detection tolerates whitespace drift:
// "We use sequenceLength * 1.5 as a heuristic to make sure we don't miss the
//  sequence if the stream is not perfectly aligned"
const targetPart = suffix.trimStart().slice(0, Math.floor(sequenceLength * 1.5));
if (buffer.length >= sequenceLength && targetPart.includes(buffer)) return;
```

**Flow:** generators compose in the StreamTransformPipeline AFTER line-stage filters: `stopAtStopTokens` guarantees no stop token byte ever escapes (hold-back window ≥ longest token); `stopAtStartOf` refuses to arm when the suffix is shorter than `sequenceLength` (nothing to collide with) and stops the moment the accumulated buffer appears anywhere inside the suffix's first 1.5× window — model output that would duplicate existing code dies silently; `onlyWhitespaceAfterEndOfLine` yields through an EOL char then cuts if the NEXT char is non-whitespace (`trim()` round-trip test), carrying a one-char pending buffer across chunk boundaries; `noFirstCharNewline` kills single-line suggestions that begin with a newline.

**Invariant:** emission lags the stream by up to `maxStopTokenLength - 1` chars — porters must keep the final `yield pending/buffer` or trailing text vanishes. `targetPart.includes(buffer)` uses CONTAINMENT both ways against a trimmed target, so whitespace-normalized near-matches still trigger; the 1.5 factor and the ≥sequenceLength arming gate are load-bearing pairs.

**Probe:** `grep -c 'maxStopTokenLength' core/autocomplete/filtering/streamTransforms/charStream.ts` → 2; `grep -c 'Math.floor(sequenceLength \* 1.5)' core/autocomplete/filtering/streamTransforms/charStream.ts` → 1; `grep -c 'if (suffix.length < sequenceLength)' core/autocomplete/filtering/streamTransforms/charStream.ts` → 1; `grep -n '  it(' core/autocomplete/filtering/streamTransforms/charStream.vitest.ts | wc -l` → 13 real cases (plain `'it('` also hits `split(/(?! )/g)` on :183/:202 = false 15).

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "stopAtStopTokens stopAtStartOf onlyWhitespaceAfterEndOfLine", limit: 8 })`

## Verdict
Adopt the hold-back-window stop-token filter, containment-based suffix collision detection with the 1.5× slack, and the EOL+non-whitespace cut with cross-chunk pending char. Tune per-language `endOfLine` lists; never emit from inside the hold-back window.
