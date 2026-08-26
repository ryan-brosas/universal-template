<!-- capsule-v2 -->
# Token-budget parse — how do you parse "+500k" / "use 2M tokens" budget directives without a JSC regex pitfall?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a user types a token target like `+500k` or `spend 2M tokens` into a prompt, how do you extract the numeric budget AND the exact spans to highlight, robustly across JS engines?

## Anchored regexes with a JSC-lookbehind avoidance and overlap dedup
**Path/Symbol:** `src/utils/tokenBudget.ts` (whole file :1-73): `parseTokenBudget` (:21-29), `findTokenBudgetPositions` (:31-64), `getBudgetContinuationMessage` (:66-73).
**Signature:** `parseTokenBudget(text: string): number | null`; `findTokenBudgetPositions(text: string): Array<{start:number; end:number}>`; `getBudgetContinuationMessage(pct, turnTokens, budget): string`.
**Data Shape:** Shorthand anchored start `^\s*+(\d+(?:\.\d+)?)\s*(k|m|b)\b` and end `\s+…(k|m|b)\s*[.!?]?\s*$`; verbose `\b(?:use|spend)\s+…\s*tokens?\b` (global variant). Multipliers `{ k:1e3, m:1e6, b:1e9 }`.

### Decisive source
```ts
// Lookbehind (?<=\s) is avoided — it defeats YARR JIT in JSC, and the
// interpreter scans O(n) even with the $ anchor. Capture the whitespace
// instead; callers offset match.index by 1 where position matters.
const SHORTHAND_END_RE = /\s\+(\d+(?:\.\d+)?)\s*(k|m|b)\s*[.!?]?\s*$/i
const VERBOSE_RE = /\b(?:use|spend)\s+(\d+(?:\.\d+)?)\s*(k|m|b)\s*tokens?\b/i

export function parseTokenBudget(text: string): number | null {
  const startMatch = text.match(SHORTHAND_START_RE)
  if (startMatch) return parseBudgetMatch(startMatch[1]!, startMatch[2]!)
  const endMatch = text.match(SHORTHAND_END_RE)
  if (endMatch) return parseBudgetMatch(endMatch[1]!, endMatch[2]!)
  const verboseMatch = text.match(VERBOSE_RE)
  if (verboseMatch) return parseBudgetMatch(verboseMatch[1]!, verboseMatch[2]!)
  return null
}
```

**Flow:** `parseTokenBudget` tries start-anchored shorthand → end-anchored shorthand → verbose, returning the first numeric match scaled by its suffix. `findTokenBudgetPositions` collects spans for all three forms, skipping an end-match span already covered by a start-match span (the `alreadyCovered` guard at :49-53) so a bare `+500k` isn't double-highlighted, then appends every verbose global match.
**Invariant:** The end-shorthand regex MUST NOT use a lookbehind — `(?<=\s)` defeats YARR JIT in JavaScriptCore (Bun) and the interpreter path scans O(n) even with the `$` anchor; instead it captures the leading `\s` and callers offset `match.index` by 1. The `+` shorthand is anchored to start/end to avoid false positives in natural language, while the verbose `use/spend … tokens` form matches anywhere. Suffix is case-insensitive (`k|m|b`), scaled by the `MULTIPLIERS` map.
**Probe:** No direct test exists for `tokenBudget.ts` (coverage caveat — source-grounded). Deterministic probes: grep-pinned comment :4-6 (JSC lookbehind rationale), :48-53 (overlap dedup guard); `search_graph` resolves `parseTokenBudget` :21-29 / `findTokenBudgetPositions` :31-64 / `getBudgetContinuationMessage` :66-73 line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "parseTokenBudget findTokenBudgetPositions token budget shorthand", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the anchored-shorthand + verbose regexes, the whitespace-capture-instead-of-lookbehind rule (JSC JIT), the start/end anchoring to avoid natural-language false positives, and the span-overlap dedup. Adapt the multiplier suffixes and the continuation-message wording. Omit nothing in the regex anchoring — removing the anchors reintroduces false positives. Coverage caveat: no direct test; behavior source-grounded.
