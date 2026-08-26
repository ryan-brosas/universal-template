<!-- capsule-v2 -->
# Slice grammar — parse `path:start[-end]` file references with fail-open-to-full degradation

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How do I accept human/LLM-written file references like `src/a.ts:10-20` and degrade safely when they are malformed?

## Four-state slice type with three distinct fail-open exits
**Path/Symbol:** `src/context/slice.ts:parseSlice` (:12–66), plus `formatSlice` (:68–73), `slicesOverlap` (:75–85), `extractSlice` (:87–101).
**Signature:** `function parseSlice(input: string): FileSlice` where `FileSlice = { path: string; sliceType: 'full'|'single-line'|'range'|'infinite-range'; startLine?: number; endLine?: number }`.
**Data Shape:** Grammar regex `/^(.+?):(\d+)(?:-(\d*))?$/` — group 1 is greedy so colons inside paths stay in the path; optional trailing empty digits (`file.ts:10-`) mean "to EOF".

### Decisive source
```ts
const SLICE_PATTERN = /^(.+?):(\d+)(?:-(\d*))?$/;

export function parseSlice(input: string): FileSlice {
  const match = input.match(SLICE_PATTERN);
  if (!match) return { path: input, sliceType: 'full' };
  const [, path, startStr, endStr] = match;
  const start = parseInt(startStr, 10);
  if (start < 1) return { path: input, sliceType: 'full' };   // lines are 1-indexed
  if (endStr === undefined) return { path, sliceType: 'single-line', startLine: start };
  if (endStr === '') return { path, sliceType: 'infinite-range', startLine: start };
  const end = parseInt(endStr, 10);
  if (end < start) return { path: input, sliceType: 'full' }; // inverted range → whole file
  return { path, sliceType: 'range', startLine: start, endLine: end };
}
```

**Flow:** match grammar → reject `start<1` (line 0 does not exist) → classify by `endStr`: undefined=single line, ''=infinite range, else numeric range → inverted `end<start` falls back to FULL. Every malformed shape degrades to reading the whole file, never throws.
**Invariant:** Malformed slices NEVER error or truncate silently to a wrong window — they widen to `full`. Overlap uses half-open-style inclusive bounds with `?? 1` / `?? Infinity` defaults; adjacent slices (`a.end < b.start`) do NOT overlap.
**Probe:** `tests/context/slice.test.ts` — pins `rejects line number 0 (lines are 1-indexed)` (:58), `rejects end < start` (:70), `accepts end == start` (:76), colon-in-directory-names paths (:51), and roundtrip parse/format (:105).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "parseSlice FileSlice sliceType", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-state union and the three fail-open-to-full exits verbatim — the degradation direction (widen, never throw) is what makes LLM-supplied references safe. Adapt the regex only if your host needs Windows drive letters (the greedy `(.+?)` already survives `C:\x` because the last `:digits$` wins). Omit nothing; this is a pure function pair.
