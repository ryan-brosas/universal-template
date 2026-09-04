<!-- capsule-v2 -->
# Bracket-matching stream filter — complete only pairs you started; suffix-close pre-seed and first-chunk closing tolerance

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does the stream filter know when to STOP before emitting a closing bracket the user's file didn't ask for — including brackets opened by a previous accepted suggestion?

## Key facts
**Path/Symbol:** `core/autocomplete/filtering/BracketMatchingService.ts` (whole, 126L) — `BRACKETS`/`BRACKETS_REVERSE` maps (:1-10), `handleAcceptedCompletion` (:19-39), `stopOnUnmatchedClosingBracket` (:41-125). Wired per-language as a `charFilters` entry (`constants/AutocompleteLanguageInfo.ts:328-341`, e.g. Json); accepted completions feed state from `CompletionProvider.ts:124`.
**Signature:** `async *stopOnUnmatchedClosingBracket(stream, prefix, suffix, filepath, multiline): AsyncGenerator<string>`; `handleAcceptedCompletion(completion, filepath)` records the stack of still-open brackets.
**Data Shape:** bracket stack of openers `["(", "{"]`; seed order matters: last-completion leftovers (multiline + same file), then current-line scan (single-line mode), then SUFFIX-derived closers unshifted to the FRONT.

### Decisive source
```ts
// :77-88 — suffix closers become PRE-seeded openers: "because we overwrite them
// and the diff is displayed, and this allows something to be edited after that"
for (let i = 0; i < suffix.length; i++) {
  if (suffix[i] === " ") continue;
  const openBracket = BRACKETS_REVERSE[suffix[i]];   // ")" → "("
  if (!openBracket) break;                            // stops at FIRST non-bracket char
  stack.unshift(openBracket);
}

// :92-104 — leading whitespace/closing brackets pass BEFORE arming:
if (!seenNonWhitespaceOrClosingBracket) {
  const idx = chunk.search(/[^\s\)\}\]]/);            // skip \s ) } ]
  ...yield chunk.slice(0, idx); seenNonWhitespaceOrClosingBracket = true;

// :111-117 — unmatched closer ⇒ truncate mid-chunk and terminate:
if (stack.length === 0 || BRACKETS[stack.pop()!] !== char) {
  yield chunk.slice(0, i); return;
}
```

**Flow:** on accept, leftover unclosed openers from the suggestion are remembered PER FILE → next completion in the same file (multiline) starts its stack with those, so multi-suggestion bracket chains stay balanced → single-line mode instead scans the CURRENT LINE (prefix tail + suffix head) for locally-opened pairs → suffix closers are pushed to the FRONT of the stack because the completion overwrites them → during streaming, any closer without a matching opener truncates the stream at that character.

**Invariant:** the class policy comment is the contract — "only completing bracket pairs that we started." The suffix pre-seed exists because emitted text visually replaces the suffix; allowing those closers lets users type INTO the overwritten region. The `break` in the suffix scan (not `continue`) means `suffix = ") foo"` seeds nothing — one non-whitespace non-closer disables all suffix seeding. Leading closers are tolerated only until the first real character.

**Probe:** `grep -c 'stack.unshift(openBracket)' core/autocomplete/filtering/BracketMatchingService.ts` → 1; `grep -c 'seenNonWhitespaceOrClosingBracket' core/autocomplete/filtering/BracketMatchingService.ts` → 3 (:91 decl, :94 gate, :100 arm); `grep -c 'openingBracketsFromLastCompletion' core/autocomplete/filtering/BracketMatchingService.ts` → 4 (:16 field, :20 reset, :37 record, :52 reuse); `grep -c 'bracketMatchingService.stopOnUnmatchedClosingBracket' core/autocomplete/constants/AutocompleteLanguageInfo.ts` → 1.

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "stopOnUnmatchedClosingBracket BracketMatchingService handleAcceptedCompletion", limit: 8 })`

## Verdict
Adopt accept-state carryover per file plus the three-seed stack (previous-completion / current-line / suffix-front) and mid-chunk truncation. Adapt which languages get the filter (upstream wires it into language charFilters, not globally).
