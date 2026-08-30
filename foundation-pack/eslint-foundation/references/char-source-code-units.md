<!-- capsule-v2 -->
# String/template code-unit mapping — how do you map a character inside a string literal back to its exact source offsets through escapes?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you locate which source text produced the Nth character of a string literal or template token (escapes, surrogates, line continuations included)?

## char-source TextReader + CodeUnit
**Path/Symbol:** `lib/rules/utils/char-source.js:TextReader` (:30–56), `CodeUnit` (:12–26), `readEscapeSequenceOrLineContinuation` (:122–159), `mapEscapeSequenceOrLineContinuation*` (:166–183), `parseStringLiteral` (:190–211), `parseTemplateToken` (:218–245).
**Signature:** `parseStringLiteral(source) → CodeUnit[]`; `parseTemplateToken(source) → CodeUnit[]`; each CodeUnit is `{ start:number, source:string }` with derived `length`/`end`.
**Data Shape:** input INCLUDES delimiting quotes/backtick; output covers only the value characters. One escape yields one CodeUnit whose `source` is the RAW escape text (`\x40`, `\u231B`) at its source position; ONE code POINT from `\u{...}` yields TWO identical-position CodeUnits (surrogate pair sharing start+source); line continuations yield ZERO units; CRLF in templates yields ONE unit with two-char source.

### Decisive source
```js
switch (str.length) {           // mapEscapeSequenceOrLineContinuation
  case 0: break;                // line continuation: no value char
  case 1: yield new CodeUnit(start, source);
  default:                      // astral code point → 2 UTF-16 units, SAME raw span
    yield new CodeUnit(start, source);
    yield new CodeUnit(start, source);
}
// octal ladder: \0–\3 read up to 3 digits, \4–\7 up to 2 — legacy octal grammar
readUnicodeSequence: /\{(?<hexDigits>[\dA-F]+)\}/iuy anchored at reader.pos,
  miss ⇒ fall back to exactly 4 hex digits (\uXXXX)
```

**Flow:** quote-aware scanner walks raw text; plain chars advance by 1; `\` dispatches to simple escapes (`__proto__:null` table), `\x`+2, `\u{...}`-or-`\uXXXX`, octal ladder, CRLF-swallowing line continuation, or identity for unknown escapes.
**Invariant:** the mapping is VALUE-character-index → SOURCE-span, not byte offsets — consumers translate regexpp Character indices into fix ranges via `offset + codeUnits[firstIndex].start` / `codeUnits[lastIndex].end`. The doubled-yield for astral points keeps index parity with UTF-16 code units while preserving the full escape as BOTH halves' source; dropping that duplication misaligns every later index. Template scanning stops at `` ` `` OR `${` (expression boundary); strings stop at the matching quote.
**Probe:** `tests/lib/rules/utils/char-source.js` (:9–159 parseStringLiteral table: surrogate pairs :17, `\u{ffff}` doubled units :37–41, line continuations :50, octal matrix :92; :161–260 parseTemplateToken twin incl. unescaped-CRLF single-unit :248).

## Consumer contract (no-misleading-character-class)
**Path/Symbol:** `lib/rules/no-misleading-character-class.js` (:362/:373/:441/:449 lazy `codeUnits ??=` memo per node).
**Flow:** rule parses once per literal on demand and converts match indices to suggestion ranges.
**Invariant:** memoization per AST node matters — parsing is O(n) and suggestions fire repeatedly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "parseStringLiteral parseTemplateToken TextReader CodeUnit", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rules.utils.char-source.parseStringLiteral" });
```

## Verdict
Adopt whole for any tool that reports positions inside string/template values; the surrogate-doubling and continuation-skip rules are the porting traps. Omit only if your AST already stores cooked-value-to-range maps.
