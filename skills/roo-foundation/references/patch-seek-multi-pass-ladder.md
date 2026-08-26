<!-- capsule-v2 -->
# seek-sequence multi-pass matcher — how do you locate patch context lines when the model's copy has whitespace or Unicode drift?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When applying an LLM-authored patch, in what order are match strictness levels attempted, and what does "match at end of file" actually pin?

## Multi-pass line-sequence search
**Path/Symbol:** `src/core/tools/apply-patch/seek-sequence.ts:seekSequence` (lines 110–153) with private helpers `exactMatch` :41, `trimEndMatch` :53, `trimMatch` :65, `normalizedMatch` :77.
**Signature:** `function seekSequence(lines: string[], pattern: string[], start: number, eof: boolean): number | null`.
**Data Shape:** inputs are whole-file lines and pattern lines (both `\n`-split, trailing empty element already dropped by the caller); returns the START INDEX of the leftmost matching window or null. `normalizeUnicode` maps typographic dashes (`\u2010-\u2015,\u2212`)→`-`, fancy quotes (`\u2018-\u201B`→`'`, `\u201C-\u201F`→`"`), and odd spaces (`\u00A0\u2002-\u200A\u202F\u205F\u3000`)→space, char-by-char after trim.

### Decisive source
```ts
const searchStart = eof && lines.length >= pattern.length ? lines.length - pattern.length : start
const maxStart = lines.length - pattern.length
// Pass 1: Exact match … Pass 2: Trim-end … Pass 3: Trim both sides … Pass 4: Unicode-normalized
for (let i = searchStart; i <= maxStart; i++) { if (exactMatch(lines, pattern, i)) return i }
```

**Flow:** empty pattern → return `start` immediately (no-op match); pattern longer than file → null; compute `searchStart` (= `maxStart` when eof, else caller cursor); run FOUR full passes over `[searchStart..maxStart]` — exact, trimEnd, trim, unicode-normalized — returning the first hit of the strictest pass that finds anything.
**Invariant:** PASS ORDER BEATS PROXIMITY: every position is tried at strictness N before any position relaxes to N+1, so a distant exact match wins over a nearby fuzzy one. The docstring claims eof mode "falls back to searching from start if needed" — IT DOES NOT: when `eof=true` the scan window IS `[maxStart..maxStart]` (single end-anchored position per pass); there is no fallback sweep from `start`. A porter who trusts the docstring will silently allow mid-file matches for `*** End of File` chunks; the code refuses them unless they sit at EOF.
**Probe:** `grep -c 'Pass [0-9]' src/core/tools/apply-patch/seek-sequence.ts` → 4 (one comment per pass); `grep -cF 'lines.length - pattern.length' src/core/tools/apply-patch/seek-sequence.ts` → 2 (searchStart + maxStart share it).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "seekSequence eof trimEnd normalizedMatch", limit: 10 });
```
(live-verified rank#1/#2 = normalizedMatch :77 / seekSequence :110).

## Verdict
Adopt the four-pass strictness ladder and pass-order-beats-proximity; adopt the single-position end-anchor for eof chunks (and fix your docstring). Adapt the Unicode table to your host's expected LLM drift. Omit nothing — the module is self-contained. Coverage caveat: NO direct unit test drives this kernel at pin (only consumers' suites); behavior pinned via source read + deterministic greps.
