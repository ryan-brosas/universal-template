<!-- capsule-v2 -->
# Pipe stdin rearrangement — differential-tolerant rebuild ladder

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When you must rewrite a piped command (e.g. to move `< /dev/null` onto its head), how do you avoid the rewriter itself injecting content bash will execute?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/bashPipeCommand.ts` — bail-out ladder (:14-100): backticks :16, `$(` :22, `$VAR` regex `/\$[A-Za-z_{]/` :30, control structures :37, joined-newlines #32515 :51, single-quote-bug :60, parse-fail :67, malformed-tokens :82; rebuild via `findFirstPipeOperator`/`buildCommandParts` (:86-99); fallback `quoteWithEvalStdinRedirect`.
**Signature:** `rearrangePipeCommand(command) → string` — either a token-verified rebuild or an eval-safe whole-quote.
**Data Shape:** ParseEntry[] tokens; output = head-segments + `< /dev/null` + tail, single-quoted for eval.

### Decisive source
```ts
// SECURITY: shell-quote tokenizes differently from bash. Input like
// `echo {"hi\":\"hi;calc.exe"}` is a bash syntax error (unbalanced quote),
// but shell-quote parses it into tokens with `;` as an operator and
// `calc.exe` as a separate word. Rebuilding from those tokens produces
// valid bash that executes `calc.exe` — turning a syntax error into an
// injection.
```

**Flow:** any of backticks / command substitution / variable references / control structures / post-join newlines ⇒ skip token surgery entirely and use the eval-quoting fallback (which preserves semantics inside one quoted arg). Otherwise: join continuations → shell-quote parse with BOTH differential detectors (single-quote backslash bug, malformed-token injection) as gates → locate the FIRST real pipe operator → rebuild `head < /dev/null | tail` preserving fd-redirection tokens as units → single-quote the result. Every gate's failure mode is the SAME conservative fallback — the rewriter never "does its best" on suspect input.

**Invariant:** (1) A command REWRITER is an injection amplifier: rebuilding from misparsed tokens launders a syntax error into executable code — only rebuild when parsing survived every named differential detector. (2) Variable references must survive round-trip: shell-quote drops `$VAR` without env, and quoting during rebuild would freeze it — so var-bearing input bypasses the rewrite. (3) One fallback for all failures keeps reasoning simple: whole-command eval-quoting preserves the original bytes. (4) The stdin redirect belongs to the PIPE HEAD, not to eval (hang fix).

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'turning a syntax error into an' src/utils/bash/bashPipeCommand.ts | head -1` → :77; `grep -nF 'See #9732' src/utils/bash/bashPipeCommand.ts | head -1` → :29; `grep -nF 'silently merging pipelines' src/utils/bash/bashPipeCommand.ts` → :48; graph resolves rearrangePipeCommand :14-100 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "rearrangePipeCommand findFirstPipeOperator buildCommandParts", limit: 5 });
```

## Verdict
Adopt the ladder verbatim for any command rewriting: enumerate unsafe-for-surgery constructs, gate on both tokenizer differentials, fall back identically everywhere.
