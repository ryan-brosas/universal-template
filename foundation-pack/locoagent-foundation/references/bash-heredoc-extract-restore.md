<!-- capsule-v2 -->
# Heredoc extract/restore — placeholder round-trip with delimiter-escape fidelity

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you hide heredoc bodies from a tokenizer that parses `<<` as two redirects, without the hiding itself becoming an injection channel?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/heredoc.ts` — salted placeholder prefix/suffix (:29-39), `HEREDOC_START_PATTERN = /(?<!<)<<(?!<)(-)?[ \t]*(?:(['"])(\\?\w+)\2|\\?(\\w+))/` (:69-71), `extractHeredocs(command, {quotedOnly})` (:113+), `restoreHeredocs` (:711), `containsHeredoc` (:731).
**Signature:** `extractHeredocs(cmd) → { processedCommand, heredocs: Map<placeholder, HeredocInfo> }`.
**Data Shape:** `HeredocInfo { fullText, delimiter, operatorStartIndex/EndIndex, contentStartIndex/EndIndex }`.

### Decisive source
```ts
// SECURITY: The backslash MUST be inside the capture group for quoted
// delimiters but OUTSIDE for unquoted ones. The old regex had \\? outside
// the capture group unconditionally, causing <<'\EOF' to extract delimiter
// "EOF" while bash uses "\EOF", allowing command smuggling.
//
// Note: Uses [ \t]* (not \s*) to avoid matching across newlines, which would be
// a security issue (could hide commands between << and the delimiter).
```

**Flow:** if no `<<`, pass through. Otherwise find heredoc starts with lookbehind/lookahead excluding bit-shift `<<<`/`<<=`, capture quoted vs escaped vs bare delimiters per bash rules, replace each whole heredoc (operator + body + closing delimiter) with `__HEREDOC_<8-byte-hex-salt>__`, hand the sanitized string to the tokenizer, then RESTORE originals by placeholder after parsing. The random salt prevents a hostile command from pre-containing a literal placeholder that restoration would substitute (argument injection). Failure mode is documented as safe: unextracted heredocs either fail shell-quote parsing or surface as extra subcommands requiring approval (:19-22).

**Invariant:** (1) Placeholder substitution must be collision-proof against attacker-chosen text — random per-parse salts, not counters. (2) Delimiter semantics are exact: quotes make backslashes LITERAL (`<<'EOF'` delimiter is `\EOF`), unquoted backslash is an ESCAPE (`<<\EOF` → `EOF`); getting this wrong lets content smuggle as delimiter lines. (3) Never use `\s` around the operator — newline-crossing matches would HIDE commands inside what you replace. (4) Restoration is byte-faithful via recorded index spans; the tokenizer never sees multi-line bodies it would mis-tokenize.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'allowing command smuggling' src/utils/bash/heredoc.ts` → :64; `grep -nF 'hide commands between' src/utils/bash/heredoc.ts` → :67; `grep -nF "randomBytes(8)" src/utils/bash/heredoc.ts` → :38; graph `search_graph --project locoagent --query extractHeredocs restoreHeredocs` → :113-687 / :711 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "extractHeredocs restoreHeredocs HEREDOC_START_PATTERN", limit: 5 });
```

## Verdict
Adopt for any pre-tokenization masking of multi-line shell constructs; port the three delimiter forms and the salt rule exactly.
