<!-- capsule-v2 -->
# VarScope tracking — statically resolving $VAR without hiding payloads

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you turn `VAR=x && cmd $VAR` into real argv for validation, without letting variables smuggle flags, paths, or empty expansions past the checks?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/ast.ts` — placeholders `__CMDSUB_OUTPUT__` (:74) / `__TRACKED_VAR__` (:82), `containsAnyPlaceholder` (:94-96), `BARE_VAR_UNSAFE_RE = /[ \t\n*?[]/` (:110), `varScope` Map (:472), scope fork at `||`/`|`/`&` (:505-563), env-prefix locality (:1254-1258), `.text` rebuild (:1316-1358), `resolveSimpleExpansion` (:1937-2008), `applyVarToScope` append poisoning (:2017-2027).
**Signature:** `resolveSimpleExpansion(node, varScope, insideString) → string | ParseForSecurityResult`.
**Data Shape:** `varScope: Map<string, string>` mapping assigned names to literal values OR placeholder sentinels.

### Decisive source
```ts
// SECURITY: Returning the actual trackedValue (not a placeholder) is the
// critical fix. `VAR=/etc && rm $VAR` → argv ['rm', '/etc'] → validatePath
// correctly rejects. Previously returned a placeholder → validatePath saw
// '__LOOP_STATIC__', resolved as cwd-relative → PASSED → bypass.
```

**Flow:** assignments feed `varScope` as the walker descends `&&`/`;` chains; `$VAR` resolution: tracked literal → returned DIRECTLY (bare args rejected if the value contains IFS/glob metachars or is EMPTY — `V="" && $V eval x` makes bash drop the field while our argv kept a phantom `""`, :1982-1988); tracked non-literal (any placeholder substring, incl. composites `prefix$(cmd)` caught by SUBSTRING not equality, :84-93) → bare = too-complex, inside strings = `__TRACKED_VAR__`; unknown `$HOME`-class vars → placeholder ONLY inside strings (:1995-2006). Env-prefix assignments (`VAR=x cmd`) stay command-local — never enter global scope (:1254-1258). After `||`/`|`/`&` the scope RESETS to the entry snapshot: conditional/background/subshell clauses must not leak assignments into later argv (flag-omission attack `true || FLAG=--dry-run && cmd $FLAG` documented :509-516). `+=` appends re-poison through `applyVarToScope`.

**Invariant:** (1) Downstream validators must see REAL values — a placeholder in argv hides the runtime path/flag from path validation (the bypass in the decisive excerpt). (2) Unquoted `$VAR` undergoes word-splitting + globbing: single-string argv lies whenever the value holds space/tab/NL/`*`/`?`/`[` — trust it ONLY inside double quotes. (3) Scope flows through `&&`/`;` (sequential bash) but forks at `||`/`|`/`&`. (4) If a resolved `$VAR` changed argv vs source text, REBUILD `.text` from shell-escaped argv (`SUB=push && git $SUB --force` must match `Bash(git push:*)` deny rules built on text, :1321-1333); also rebuild when the span contains a newline — line continuations are invisible to argv but preserved in `.text`, breaking prefix matching (:1342-1348).

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'treated as non-literal (conservative)' src/utils/bash/ast.ts` → :92; `grep -nF 'critical fix' src/utils/bash/ast.ts` → :1963; `grep -nF 'phantom' src/utils/bash/ast.ts` → :1986; `grep -nF 'deny rule matching on base command name' src/utils/bash/ast.ts` → :293; graph `search_graph --project locoagent --query resolveSimpleExpansion` → ast.ts :1937-2008 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "resolveSimpleExpansion applyVarToScope containsAnyPlaceholder walkVariableAssignment", limit: 5 });
```

## Verdict
Adopt whole: literal-through, sentinel-for-runtime, substring placeholder poisoning, bare-arg metachar rejection, scope forking at non-sequential separators, and argv-derived text rebuild. This is THE reusable contract for allowing benign variable use under static permission checking.
