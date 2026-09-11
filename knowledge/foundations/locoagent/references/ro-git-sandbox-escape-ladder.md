<!-- capsule-v2 -->
# Git sandbox-escape ladder — five independent gates that stop "create fake git internals, then run git" hook execution

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Git executes hooks from the current repo's filesystem — how do you stop a compound command from planting HEAD/hooks/refs and then invoking git against them?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/readOnlyValidation.ts` — `GIT_INTERNAL_PATTERNS` (:1771-1776), `isGitInternalPath` (:1781-1785), `NON_CREATING_WRITE_COMMANDS` (:1788), `extractWritePathsFromSubcommand` via PATH_EXTRACTORS/COMMAND_OPERATION_TYPE (:1795-1823), `commandWritesToGitInternalPaths` incl. extractOutputRedirections (:1840-1864), `commandHasAnyGit` via splitCommand_DEPRECATED + isNormalizedGitCommand (:1760-1764), the five-gate export `checkReadOnlyConstraints` (:1876-1990).
**Signature:** `checkReadOnlyConstraints(input: z.infer<typeof BashTool.inputSchema>, compoundCommandHasCd: boolean): PermissionResult` — behaviors: `'allow'` | `'passthrough'` (never 'ask' except UNC).
**Data Shape:** PermissionResult `{ behavior, message?, updatedInput? }`; git-internal = `/^HEAD$/`, `/^objects(\/|$)/`, `/^refs(\/|$)/`, `/^hooks(\/|$)/` after stripping leading `./`.

### Decisive source
```ts
// SECURITY: A compound command could bypass the bare repo detection by:
// 1. Creating bare git repo files (HEAD, objects/, refs/, hooks/) in the same command
// 2. Then running git, which would execute malicious hooks
//
// Example attack:
// mkdir -p objects refs hooks && echo '#!/bin/bash\nmalicious' > hooks/pre-commit && touch HEAD && git status
```
And the race gate:
```ts
// SECURITY: Only auto-allow git commands as read-only if we're in the original cwd
// (which is protected by sandbox denyWrite) or if sandbox is disabled (attack is moot).
// Race condition: a sandboxed command can create bare repo files in a subdirectory,
// and a backgrounded git command (e.g. sleep 10 && git status) would pass the
// isCurrentDirectoryBareGitRepo() check at evaluation time before the files exist.
```

**Flow:** parse-fail ⇒ passthrough → whole-command safety pre-check BEFORE splitting (splitCommand_DEPRECATED transforms `${VAR}`→`$VAR`) → UNC ⇒ ask → compute hasGitCommand once → gate 1: cd ∧ git ⇒ passthrough (fake-hooks dir) → gate 2: git ∧ cwd-is-bare-repo ⇒ passthrough (deleted .git/HEAD + planted hooks) → gate 3: git ∧ compound-writes-git-internal-paths (PATH_EXTRACTORS write paths + output redirections; rm/rmdir/sed excluded as non-creating) ⇒ passthrough → gate 4: sandboxing enabled ∧ cwd ≠ originalCwd ∧ git ⇒ passthrough (evaluation-time TOCTOU) → all subcommands read-only ⇒ allow, else passthrough.

**Invariant:** (1) Every gate returns PASSTHROUGH (escalate to rule engine / user), never 'allow' with a warning — fail open to MORE scrutiny. (2) The check must run on the ORIGINAL string before any transformation that changes token shapes. (3) Write-path extraction distinguishes creating writes (mkdir/touch/cp/mv/redirects) from non-creating ones (rm/sed -i) — only creators can plant a repo. (4) Time-of-check/time-of-use is handled by denying the SITUATION (git outside protected cwd under sandbox), not by trying to win the race. (5) This function is also BashTool.isReadOnly — which feeds isConcurrencySafe, so a wrong 'allow' both skips permission AND parallelizes an unsafe command.

**Probe:** no upstream tests reachable (`tests/` = shell scripts) — coverage caveat. Pins from repo root: `grep -nF "hooks/pre-commit && touch HEAD && git status" src/tools/BashTool/readOnlyValidation.ts` → :1835; `grep -nF "NON_CREATING_WRITE_COMMANDS = new Set(['rm', 'rmdir', 'sed'])" src/tools/BashTool/readOnlyValidation.ts` → :1788; consumer wiring: `grep -nF "behavior === 'allow'" src/tools/BashTool/BashTool.tsx` → :440 inside `isReadOnly` (:437-441).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "commandWritesToGitInternalPaths isGitInternalPath GIT_INTERNAL_PATTERNS", limit: 4 });
// → isGitInternalPath :1781-1785 + commandWritesToGitInternalPaths :1840-1864 line-exact (total:2)
```

## Verdict
Adopt the five-gate ladder and its ordering (cheap syntactic checks first, environment-dependent last). Adapt PATH_EXTRACTORS to your command inventory. Omit the SandboxManager coupling only if your host has no sandbox concept — then keep gate 4's comment explaining what it covered.
