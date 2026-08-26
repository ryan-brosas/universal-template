<!-- capsule-v2 -->
# Shell-quote differential hardening — parser-vs-shell mismatches as a class

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When you depend on a third-party shell tokenizer for security decisions, how do you defend against the places its parsing differs from bash?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/shellQuote.ts` — `tryParseShellCommand` (:24-45), `hasMalformedTokens` (:117-188), `hasShellQuoteSingleQuoteBug` (:190-265), `quote` JSON-fallback ban (:279-304); consumers `bashPipeCommand.rearrangePipeCommand` (:14-100), legacy `splitCommandWithOperators` (commands.ts :85+).
**Signature:** `hasMalformedTokens(command, parsed) → boolean`; `hasShellQuoteSingleQuoteBug(command) → boolean` — both walk RAW command text with bash semantics, not the tokens.
**Data Shape:** `ParseEntry[]` from shell-quote; checks operate on token balance counts.

### Decisive source
```ts
//   Odd trailing \'s = always a bug:
//   '\\' -> shell-quote: \' = literal ', still open. bash: \, closed.
// ...
//   Even trailing \'s = bug ONLY when a later ' exists in the command:
//   Detail: the regex alternation tries \' before [^']. For '\\', it matches
//   the first \ via [^'] (next char is \, not '), then the second \'
//   (next char IS '). This consumes the closing '. ... See H1 report:
//   git ls-remote 'safe\' '--upload-pack=evil' 'repo'
```

**Flow:** THREE independent differentials, each fail-closed to whole-command handling: ① **single-quote backslash bug** — shell-quote's chunker treats `\'` inside single quotes as an escape while bash treats backslash as literal; odd trailing backslashes before a closing quote are ALWAYS a bug, even ones only when a later `'` exists for the regex to consume (H1: `git ls-remote 'safe\' '--upload-pack=evil' 'repo'` merges the payload into one token). ② **malformed-token injection** (H1 #3482049) — ambiguous input like `echo {"hi":"hi;evil"}` is a bash SYNTAX ERROR but shell-quote parses it happily with `;` as an operator; rebuilding from those tokens turns a syntax error into valid bash executing calc.exe. Detection: raw-command quote-parity walk (shell-quote silently DROPS unmatched quotes) + per-token brace/paren/bracket/quote balance. ③ **quoting fallback ban** — on strict-quote validation failure never fall back to JSON.stringify: double quotes don't stop shell execution (`"echo" "$(whoami)"`). Same class in bashPipeCommand: `$VAR` references dropped-to-empty by parse-without-env ⇒ bail to eval-quoting (#9732).

**Invariant:** (1) A tokenizer used for SECURITY must be treated as adversarially wrong wherever its grammar differs from the real shell — every known differential needs a named detector that fails CLOSED (fall back to conservative whole-command handling), not a patch attempt. (2) Syntax errors are safe; silent misparses are not — detect the transformation of errors into executable input. (3) Token-level checks can't see dropped characters: verify parity on the RAW string with real bash semantics. (4) Never let a quoting library's convenience fallback weaken output guarantees — reject instead.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'chunker regex' src/utils/bash/shellQuote.ts | head -1` → :214; `grep -nF '#3482049' src/utils/bash/shellQuote.ts | head -1` → :114; `grep -nF 'Never use JSON.stringify as a fallback' src/utils/bash/shellQuote.ts` → :296; graph `search_graph --project locoagent --query hasShellQuoteSingleQuoteBug hasMalformedTokens` → :190-265 / :117-188 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "hasShellQuoteSingleQuoteBug hasMalformedTokens tryParseShellCommand", limit: 5 });
```

## Verdict
Adopt the differential-detector pattern (named check per known mismatch, each failing closed) plus the two H1 detectors verbatim whenever shell-quote or similar feeds permission logic.
