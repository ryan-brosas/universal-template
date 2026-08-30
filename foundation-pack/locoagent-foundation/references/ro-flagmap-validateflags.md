<!-- capsule-v2 -->
# Shared read-only flag map & validator — how do you prove an external command's flags are safe without re-implementing every CLI's getopt?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a command is allowlisted as "read-only", how do you validate its flags against what the REAL binary will parse, given GNU getopt semantics differ from naive token walking?

## Path/Symbol
**Path/Symbol:** `src/utils/shell/readOnlyCommandValidation.ts` — `FlagArgType` union (:18-24), `ExternalCommandConfig` (:26-38), shared git flag groups GIT_STAT_FLAGS/GIT_COLOR_FLAGS/GIT_PATCH_FLAGS etc. (:44-101), `GIT_READ_ONLY_COMMANDS` map (:107-923), `GH_READ_ONLY_COMMANDS` (:984-1380), `DOCKER_READ_ONLY_COMMANDS` (:1386-1410), `RIPGREP_READ_ONLY_COMMANDS` (:1416-1498), `PYRIGHT_READ_ONLY_COMMANDS` (:1504-1531), `validateFlagArgument` (:1650-1670), `validateFlags` (:1684-1893).
**Signature:** `validateFlags(tokens: string[], startIndex: number, config: ExternalCommandConfig, options?: { commandName?: string; rawCommand?: string; xargsTargetCommands?: string[] }): boolean`.
**Data Shape:** `FlagArgType = 'none' | 'number' | 'string' | 'char' | '{}' | 'EOF'`; config = `{ safeFlags: Record<string, FlagArgType>, additionalCommandIsDangerousCallback?, respectsDoubleDash? }`. Maps are keyed by multi-word prefixes (`'git diff'`, `'git stash list'`) — longer keys MUST be matched first.

### Decisive source
```ts
export type FlagArgType =
  | 'none' // No argument (--color, -n)
  | 'number' // Integer argument (--context=3)
  | 'string' // Any string argument (--relative=path)
  | 'char' // Single character (delimiter)
  | '{}' // Literal "{}" only
  | 'EOF' // Literal "EOF" only
```
And the `--` contract:
```ts
if (token === '--') {
  // SECURITY: Only break if the tool respects POSIX `--` (default: true).
  // Tools like pyright don't respect `--` — they treat it as a file path
  // and continue processing subsequent tokens as flags. Breaking here
  // would let `pyright -- --createstub os` auto-approve a file-write flag.
  if (config.respectsDoubleDash !== false) {
    i++
    break // Everything after -- is arguments
  }
```

**Flow:** consumer tokenizes via shell-quote → finds longest matching key in the config map → walks tokens from after the command prefix → per flag: split on first `=`, look up FlagArgType, unknown flags fall through to git `-<num>` shorthand / grep+rg attached-numeric (`-A20`) / bundle handling → validate value type → non-flag tokens are positionals (allowed unless a callback says otherwise). The same maps + `validateFlags` serve BashTool AND PowerShellTool (PS imports GIT/GH/DOCKER/RIPGREP/PYRIGHT maps and calls `validateFlags` at its own :1700/:1726).

**Invariant:** (1) Flag maps must model the BINARY's getopt, not your tokenizer — every parser differential below is a case where validator and binary disagreed about who consumes the next argv. (2) `respectsDoubleDash: false` exists because pyright treats `--` as a path; breaking there would auto-approve post-`--` write flags. (3) `'{}'` and `'EOF'` literal-only types exist for xargs `-I`/`-E` where free strings would be target-command confusion. (4) Longest-prefix-first ordering is load-bearing: `'git remote show'` before `'git remote'`, else bare-remote rules swallow show. (5) Positional fallthrough is DANGEROUS for commands with write-capable positionals (git tag/branch/reflog) — those need `additionalCommandIsDangerousCallback`.

**Probe:** no upstream unit tests reachable (`tests/` holds shell scripts only) — coverage caveat stands. Deterministic pins from repo root: `grep -nF "Literal \"{}\" only" src/utils/shell/readOnlyCommandValidation.ts` → :23; `grep -cn "FlagArgType =" src/utils/shell/readOnlyCommandValidation.ts` → 1; graph search `validateFlags` → readOnlyCommandValidation.ts :1684-1893 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "validateFlags validateFlagArgument FLAG_PATTERN", limit: 6 });
// → validateFlags :1684-1893, validateFlagArgument :1650-1670 line-exact
```

## Verdict
Adopt the typed-flag-map architecture (one declarative table per CLI, one walker) and the six FlagArgType values including literal-only types. Adapt the specific flag inventories to the binaries your host ships. Omit nothing structural — the exclusions documented in the maps (e.g. `--server-option`, `-o`) are themselves the security content.
