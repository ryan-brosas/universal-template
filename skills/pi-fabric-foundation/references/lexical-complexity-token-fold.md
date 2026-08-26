<!-- capsule-v2 -->
# Lexical complexity token fold — how do you measure code complexity without an AST?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How is a statement-decision count computed cheaply and deterministically over TS/JS/TSX/JSX without pulling in a parser?

## Lexical complexity token fold
**Path/Symbol:** `src/state/complexity.ts:countTypeScriptJavaScript/tokenize` (:246–288, :66–241); ledger consumption in `src/state/store.ts` (:1044–1106).
**Signature:** `countFileComplexity(file): {file, language: "typescript/javascript", count} | undefined` — undefined for unsupported extensions; `LanguageComplexity.count(source): number`.
**Data Shape:** counts ONLY the keyword tokens `if` (incl. `else if`), `case`, `default`, `catch`, `for`, `while`; ternaries/`&&`/`||`/`?.`/`??` NEVER count. Store persists per-file ledgers under key prefix `state/complexity/<file>` `{file, language, count, lastDelta, ts}`.

### Decisive source
```ts
// header comment pins the contract:
// Strings, template/JSX text, regular-expression literals, and comments are
// skipped; code inside ${...} is tokenized. ... This is intentionally a token
// fold, not an AST or a prose regex.
if (switchBodies[switchBodies.length - 1] === true) {
      if (token === "default" && followedBy(tokens, index, ":")) {
        count++;
      } else if (token === "case") {
```

**Flow:** hand-rolled scanner emits word/punctuation tokens while skipping strings/comments/regex literals (regex-vs-divide disambiguated by the previous token via a 13-word prefix set) and recursing into JSX + `${...}` template holes → counting pass walks tokens with a brace-stack of "is switch body" booleans → store's prepareComplexity diffs measured count vs persisted ledger and records `{previous, current, delta, baseline}`.
**Invariant:** `case`/`default` count only inside a switch body (`waitingForSwitchBody` flag consumed by the next `{`, pushed per open brace); `default` additionally requires a following `:` (so object keys named default never count); `if`/`for`/`while` require a following `(`; `catch` accepts `(` or bare `{`. First measurement sets `baseline: true` with delta 0 — a fresh file never reports a fake regression.
**Probe:** `grep -c 'regularExpressionPrefixWords' src/state/complexity.ts` → 2 (declaration + use); `grep -c 'baseline: previous === undefined' src/state/store.ts` → 1. Upstream suite: tests/state-*.test.ts exercise the store plane; no dedicated tokenizer unit file (coverage caveat: tokenizer pinned by the in-header contract + store integration).
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "countFileComplexity tokenize switch case complexity ledger", limit: 10 });
// tokenize Function src/state/complexity.ts 66-241
```

## Verdict
Adopt the token-fold + switch-body stack when you need parser-free deterministic complexity deltas in an agent harness; adapt counted tokens to your language set; omit the regex-literal scanner only if your inputs are guaranteed literal-free (they aren't for real source).
