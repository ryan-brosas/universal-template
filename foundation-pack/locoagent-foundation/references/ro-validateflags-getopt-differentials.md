<!-- capsule-v2 -->
# validateFlags getopt differentials — the four parser bugs where the validator and the binary disagreed on who eats the next argv

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Where exactly does naive flag-walking diverge from GNU getopt, and what is the general rule that closes every divergence?

## Path/Symbol
**Path/Symbol:** `src/utils/shell/readOnlyCommandValidation.ts` inside `validateFlags` — hasEquals split (:1733-1760), `-E=` empty-inline fix comment (:1741-1754), bundle rejection (:1796-1831), git `-<num>` shorthand (:1762-1768), grep/rg attached-numeric (:1770-1794), string-arg dash rejection + `--sort` exception (:1863-1879); `'git diff'` -S/-G/-O required-arg entry (:160-171).
**Signature:** same walker as ro-flagmap-validateflags; this capsule covers its differential class.
**Data Shape:** `hasEquals: boolean` (token CONTAINS `=`), `inlineValue: string` (value after first `=`, possibly empty).

### Decisive source
```ts
// SECURITY: Track whether the token CONTAINS `=` separately from
// whether the value is non-empty. `-E=` has `hasEquals=true` but
// `inlineValue=''` (falsy). Without `hasEquals`, the falsy check at
// line ~1813 would fall through to "consume next token" — but GNU
// getopt for short options with mandatory arg sees `-E=` as `-E` with
// ATTACHED arg `=` (it doesn't strip `=` for short options). Parser
// differential: validator advances 2 tokens, GNU advances 1.
//
// Attack: `xargs -E= EOF echo foo` (zero permissions)
//   Validator: inlineValue='' falsy → consumes EOF as -E arg → i+=2 →
//     echo ∈ SAFE_TARGET_COMMANDS_FOR_XARGS → break → AUTO-ALLOWED
//   GNU xargs: -E attached arg=`=` → EOF is TARGET COMMAND → CODE EXEC
```
And the bundle rule:
```ts
// Fix: require ALL bundled flags to have arg type 'none'. If any bundled
// flag requires an argument (non-'none' type), reject the whole bundle.
// This is conservative — it blocks `-rI` (xargs) entirely, but that's
// the safe direction.
```

**Flow:** four documented differentials, each a validator-vs-binary disagreement about argv consumption: (1) `-S -- --output=x`: validator treats -S as no-arg and breaks at `--`; git consumes `--` AS the pickaxe string → arbitrary file write (fix: -S/-G/-O are 'string'). (2) `-E= EOF echo`: falsy-empty inline value consumed the next token; GNU consumed nothing extra (fix: hasEquals ⇒ use inlineValue even when empty). (3) `-rI echo sh -c id`: arg-taking flag LAST in a bundle consumes the NEXT argv as ITS argument; validator's naive existence-check thought `echo` was the xargs target while xargs ran `sh -c id` → RCE (fix: bundles may contain ONLY 'none'-type flags). (4) `pyright -- --createstub os`: tool doesn't respect `--`, so breaking endorses post-`--` write flags (fix: respectsDoubleDash:false keeps validating).

**Invariant:** THE RULE: whenever your tokenizer's cursor advance differs from the binary's for ANY input, whatever your validator skips unexamined is attacker-controlled. Close each differential in the direction of consuming LESS or validating MORE, never by widening trust. Empty-string values are real values (`hasEquals`, not truthiness). Bundles inherit their most dangerous member. Required-arg short flags consume the next argv UNCONDITIONALLY — even when it looks like `--`.

**Probe:** no upstream tests reachable — coverage caveat. Pins from repo root: `grep -nF "Arg-taking flag in a bundle — cannot safely validate" src/utils/shell/readOnlyCommandValidation.ts` → :1823.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "validateFlags FlagArgType safe flags", limit: 6 });
// → validateFlags :1684-1893 (walker containing all four fixes)
```

## Verdict
Adopt all four closures verbatim if you walk flags for any allowlist system; they are each backed by a concrete exploit string in comments. Adapt command names/types to your host. Omit the grep/rg attached-numeric special case only if you have no such commands.
