<!-- capsule-v2 -->
# Eval-like builtin blocklist — argv-abstraction escapes

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Which commands LOOK inert as `['name', 'string-arg']` argv but execute their arguments as code, and how do you catch the ones that hide inside single-quoted operands?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/ast.ts` — `EVAL_LIKE_BUILTINS` (:2086-2134), `ZSH_DANGEROUS_BUILTINS` (:2060-2078), `SUBSCRIPT_EVAL_FLAGS` (:2143-2155), `TEST_ARITH_CMP_OPS` (:2169), `BARE_SUBSCRIPT_NAME_BUILTINS` (:2182), `READ_DATA_FLAGS` (:2189), `walkArithmetic` (:1675), enforced per-command inside `checkSemantics` (:2458-2679 tail).
**Signature:** `checkSemantics(commands: SimpleCommand[]) → { ok: true } | { ok: false, reason }` — operates on RESOLVED argv (post wrapper-strip, post $VAR resolution).
**Data Shape:** name-keyed Sets/Records; `SUBSCRIPT_EVAL_FLAGS: Record<builtin, Set<flag>>` maps each builtin to the flags whose NEXT argument is a NAME operand.

### Decisive source
```ts
// `trap 'cmd' SIGNAL` — cmd runs as shell code on signal/exit. EXIT fires
// at end of every BashTool invocation, so this is guaranteed execution.
'trap',
// `enable -f /path/lib.so name` — dlopen arbitrary .so as a builtin.
// Native code execution.
'enable',
```

**Flow:** for each resolved command: argv[0] ∈ EVAL_LIKE_BUILTINS (eval/source/./exec/command/builtin/fc/coproc/noglob/nocorrect/trap/enable/mapfile/readarray/hash/bind/complete/compgen/alias/let) or ZSH_DANGEROUS_BUILTINS (zmodload gateway + zf_* file ops; `\zmodload` matched via walkArgument's backslash-aware path :1413) ⇒ reject. THEN the subscript-eval family: `test -v`/`printf -v`/`read -a`/`unset -v`/`wait -p` (bash ≥5.1, verified on 5.3.9 per comment :2150-2153) take a NAME operand that bash ARITHMETICALLY evaluates — `'a[$(id)]'` executes id even though tree-sitter sees an opaque single-quoted leaf. Check BOTH separate form (`-v NAME`) and fused combined flags (`-ra` ⇒ `-a` present, :2439-2458); `[[ x -eq y ]]` evaluates BOTH sides arithmetically (:2157-2169) so operand position doesn't matter; `read`/`unset` treat EVERY positional as a NAME (:2172-2189). `let EXPR` ≡ `$(( EXPR ))` (:2128-2133); standalone arithmetic walks guard `$(( ))` via walkArithmetic (vidarholen arithmetic-injection reference :1669).

**Invariant:** (1) Any construct that re-parses a STRING as shell/arith code escapes the argv abstraction — argv-level allowlists are blind to it; block by resolved NAME, not syntax shape. (2) Quoting is NOT a boundary for these operands: single quotes defeat the PARSER's view, not bash's subscript evaluation. (3) Over-blocking is the safe side (`[`/`test` normalized together get the `[[` check too, :2165-2167). (4) This tier must apply whenever semantics are checked — which is exactly why parse-ABORT must not degrade to a code path lacking it (cross-ref bash-parser-abort-sentinel).

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'guaranteed execution' src/utils/bash/ast.ts` → :2105; `grep -nF 'command-lookup cache' src/utils/bash/ast.ts`; `grep -c 'zf_' src/utils/bash/ast.ts` ≥ 8; `grep -nF "executes id" src/utils/bash/ast.ts | head -1` → :2130; graph `search_graph --project locoagent --query checkSemantics` → ast.ts :2213-2679 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "EVAL_LIKE_BUILTINS ZSH_DANGEROUS_BUILTINS SUBSCRIPT_EVAL_FLAGS walkArithmetic", limit: 5 });
```

## Verdict
Adopt the two-tier design: a flat eval-like name blocklist PLUS a per-builtin NAME-operand subscript table with combined-flag expansion. Re-derive membership for your shell targets; keep the verified-version citations in comments.
