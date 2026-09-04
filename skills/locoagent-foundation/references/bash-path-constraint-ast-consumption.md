<!-- capsule-v2 -->
# AST path-constraint consumption — argv/redirects straight from the tree

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How should a path validator consume AST output instead of re-parsing command strings with a buggy tokenizer?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/pathValidation.ts` — `checkPathConstraints(input, cwd, ctx, compoundCommandHasCd?, astRedirects?, astCommands?)` (:1013-1109), `astRedirectsToOutputRedirections` (:1116-1150), argv-level `validateSinglePathCommandArgv` (:1077-1088), process-substitution regex gate (:1021-1038).
**Signature:** `→ PermissionResult` (passthrough when clean; deny/ask otherwise).
**Data Shape:** consumes `Redirect[]` + `SimpleCommand[]` produced by parseForSecurity; falls back to string re-parse only when AST absent.

### Decisive source
```ts
// SECURITY: When AST-derived commands are available, iterate them with
// pre-parsed argv instead of re-parsing via splitCommand_DEPRECATED + shell-quote.
// shell-quote has a single-quote backslash bug that causes
// parseCommandArguments to silently return [] and skip path validation
// (isDangerousRemovalPath etc). The AST already resolved argv correctly.
```

**Flow:** if NO AST: regex-ask any process substitution (`>(`/`<(` can execute commands writing to hidden targets — e.g. `echo secret > >(tee .git/config)`); WITH AST this is redundant (process_substitution ∈ DANGEROUS_TYPES ⇒ too-complex upstream). Convert AST redirects: `>`/`>|`/`&>` → `>`; `>>`/`&>>` → `>>`; fd-dups (`2>&1`) excluded. Expansion-bearing redirect targets (`$VAR`, `%VAR%`) ⇒ ask (unvalidatable target). Then validate each command's PATHS from pre-resolved argv (`rm`/`mv`/dangerous-path checks) — the argv tier replaces shell-quote re-tokenization whose silent `[]` result skipped isDangerousRemovalPath checks entirely.

**Invariant:** (1) Re-tokenizing for validation reintroduces every tokenizer differential the AST pass already survived — consume resolved argv/redirects directly whenever present. (2) A validator must remain total: keep the legacy string path for parse-unavailable mode but treat its known-broken cases as ask, not allow. (3) Redirect operator families collapse by EFFECT (> family writes/truncates, >> family appends) and fd duplication is not a file write. (4) Process substitution is a hidden-writer channel on the legacy path.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'silently return [] and skip path validation' src/tools/BashTool/pathValidation.ts` → hits :886 (doc) + :1075 (code); `grep -nF 'tee .git/config' src/tools/BashTool/pathValidation.ts` → :1023; graph resolves checkPathConstraints :1013-1109 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "checkPathConstraints astRedirectsToOutputRedirections validateSinglePathCommandArgv", limit: 5 });
```

## Verdict
Adopt the dual-tier shape: AST-first consumption with a conservative string fallback whose known failure modes degrade to asks. The redirect-family mapping table ports as-is.
